# -*- coding: utf-8 -*-
"""
This file extends the core Odoo Project module by inheriting the Project Updates feature.
It adds a comprehensive profitability dashboard, including HR cost calculation, facilities, taxes,
and margin analysis, directly into the project interface.

Note:
- The 'project.project' model is inherited to inject advanced financial KPIs.
- The Project Updates action and views are customized for enhanced reporting and usability.
- All enhancements are fully integrated with the standard Odoo Project Updates workflow.

Odoo 18 Compatibility:
- Updated profitability_items structure to use revenues/costs format
- Updated _get_stat_buttons to use 'sequence' instead of 'order'
- Added sold_items for Contract Terms section (ported from Odoo 15)
"""

from odoo import api, models, fields
from odoo.tools import format_amount
from odoo.tools.misc import formatLang
import json
import logging

_logger = logging.getLogger(__name__)


class Project(models.Model):
    _inherit = 'project.project'

    # 1. Stored Profitability Fields for Performance
    company_currency_id = fields.Many2one(
        related='company_id.currency_id', 
        string='Company Currency'
    )
    x_net_value = fields.Monetary(
        compute='_compute_profitability_metrics', 
        store=True, 
        currency_field='company_currency_id', 
        string="Untaxed Amount"
    )
    x_total_hr_cost = fields.Monetary(
        compute='_compute_profitability_metrics', 
        store=True, 
        currency_field='company_currency_id', 
        string="HR Costs"
    )
    x_facilities_cost = fields.Monetary(
        compute='_compute_profitability_metrics', 
        store=True, 
        currency_field='company_currency_id', 
        string="Facilities Costs"
    )
    x_travel_lodging = fields.Monetary(
        compute='_compute_profitability_metrics', 
        store=True, 
        currency_field='company_currency_id', 
        string="Travel & Lodging"
    )
    x_other_costs = fields.Monetary(
        compute='_compute_profitability_metrics', 
        store=True, 
        currency_field='company_currency_id', 
        string="Other Costs"
    )
    x_final_margin = fields.Monetary(
        compute='_compute_profitability_metrics', 
        store=True, 
        currency_field='company_currency_id', 
        string="Final Margin"
    )
    x_total_taxes = fields.Monetary(
        compute='_compute_profitability_metrics', 
        store=True, 
        currency_field='company_currency_id', 
        string="Total Taxes"
    )
    x_hr_cost_warning = fields.Text(
        compute='_compute_profitability_metrics', 
        store=True, 
        string="HR Cost Warning"
    )

    @api.depends(
        'timesheet_ids.unit_amount',
        'timesheet_ids.employee_id.hourly_cost',
        'sale_order_id.order_line', 
        'sale_order_id.custom_total_net_sum',
        'sale_order_id.business_trip_ids.final_total_cost'
    )    
    def _compute_profitability_metrics(self):
        """
        Computes all profitability metrics and stores them.
        This method is triggered when the underlying analytic lines (timesheets, invoice lines) change.
        """
        for project in self:
            sale_orders = project._get_sale_orders()
            
            # --- HR Cost Calculation (Self-Contained Logic) ---
            timesheet_data = self.env['account.analytic.line'].read_group(
                [('project_id', '=', project.id), ('employee_id', '!=', False)],
                ['unit_amount:sum', 'employee_id'],
                ['employee_id'],
                lazy=False
            )
            total_hr_cost = 0.0
            employees_without_cost = []
            
            if timesheet_data:
                employee_ids = [d['employee_id'][0] for d in timesheet_data]
                # In Odoo 16+, 'timesheet_cost' was renamed to 'hourly_cost'
                employee_costs = {emp.id: emp.hourly_cost for emp in self.env['hr.employee'].browse(employee_ids)}
                for line in timesheet_data:
                    employee_id = line['employee_id'][0]
                    employee_name = line['employee_id'][1]
                    hours = line['unit_amount']
                    rate = employee_costs.get(employee_id, 0)
                    if not rate:
                        employees_without_cost.append(str(employee_name))
                    total_hr_cost += hours * rate
            
            project.x_total_hr_cost = total_hr_cost
            
            # Set warning message for employees without timesheet cost
            if employees_without_cost:
                unique_names = sorted(list(set(employees_without_cost)))
                project.x_hr_cost_warning = """
The following employees have zero hourly rates, which may affect the accuracy of HR cost calculations:

• %s

Please verify and update their timesheet costs in the HR module to ensure accurate project profitability analysis.
                """.strip() % "\n• ".join(unique_names)
            else:
                project.x_hr_cost_warning = False
            
            # --- Other Metrics Calculation ---
            # Facilities cost is 15% of HR cost (hardcoded value, consider making configurable)
            project.x_facilities_cost = total_hr_cost * 0.15

            project.x_net_value = sum(order.amount_untaxed for order in sale_orders)
            project.x_total_taxes = sum(order.amount_tax for order in sale_orders)
            project.x_other_costs = sum(order.custom_total_net_sum for order in sale_orders if hasattr(order, 'custom_total_net_sum'))
            
            # Travel & Lodging (safe check for business trip module)
            travel_lodging = 0.0
            if 'business.trip' in self.env:
                try:
                    # Define the states for which costs should be included
                    valid_trip_states = [
                        'organization_done',         # Organization Completed
                        'in_progress',               # Travel in Progress
                        'completed_waiting_expense', # Awaiting Travel Expenses
                        'expense_submitted',         # Expenses Under Review
                        'completed'                  # TRAVEL PROCESS COMPLETED
                    ]
                    
                    # Build search domain to find all business trips related to this project
                    trip_domain = [
                        ('trip_status', 'in', valid_trip_states),
                        '|', '|',
                        # Trips linked via sale orders
                        ('sale_order_id', 'in', sale_orders.ids if sale_orders else []),
                        # Standalone trips linked directly to this project
                        ('selected_project_id', '=', project.id),
                        # Trips where project was created for business trip
                        ('business_trip_project_id', '=', project.id),
                    ]
                    
                    related_trips = self.env['business.trip'].search(trip_domain)
                    
                    # Sum the final_total_cost from the retrieved trips
                    travel_lodging = sum(related_trips.mapped('final_total_cost'))

                except Exception as e:
                    _logger.warning("Error calculating travel/lodging costs for project %s: %s", project.id, e)
                    travel_lodging = 0.0
            project.x_travel_lodging = travel_lodging

            project.x_final_margin = (
                project.x_net_value - 
                (project.x_total_hr_cost + project.x_facilities_cost + project.x_travel_lodging + project.x_other_costs)
            )

    def action_open_payment_report(self):
        """
        Open a popup window showing the Summary of HR Costs report for the current project.
        """
        self.ensure_one()
        # Generate or refresh report lines for this project
        self.env['custom.project.profitability.dashboard'].generate_report_lines(self.id)
        return {
            'name': 'Summary of HR Costs',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.project.profitability.dashboard',
            'view_mode': 'list',
            'target': 'new',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def _get_profitability_labels(self):
        """
        Override to add custom labels for profitability items.
        """
        labels = super()._get_profitability_labels()
        labels.update({
            'custom_hr_costs': self.env._('HR Costs'),
            'custom_facilities': self.env._('Facilities Costs'),
            'custom_travel': self.env._('Travel & Lodging'),
            'custom_other': self.env._('Other Costs'),
            'custom_margin': self.env._('Margin'),
            'custom_taxes': self.env._('Taxes'),
        })
        return labels

    def _get_profitability_sequence_per_invoice_type(self):
        """
        Override to add custom sequence for our profitability items.
        """
        sequence = super()._get_profitability_sequence_per_invoice_type()
        sequence.update({
            'custom_hr_costs': 50,
            'custom_facilities': 51,
            'custom_travel': 52,
            'custom_other': 53,
        })
        return sequence

    def _get_profitability_items(self, with_action=True):
        """
        Override to add custom profitability items (HR costs, facilities, travel, etc.)
        to the standard profitability panel.
        
        Odoo 18 format:
        {
            'revenues': {'data': [...], 'total': {'invoiced': 0.0, 'to_invoice': 0.0}},
            'costs': {'data': [...], 'total': {'billed': 0.0, 'to_bill': 0.0}}
        }
        """
        profitability_items = super()._get_profitability_items(with_action)
        
        # Force recomputation to ensure fresh values
        self._compute_profitability_metrics()
        
        sequence = self._get_profitability_sequence_per_invoice_type()
        
        # Add HR Costs to costs section
        if self.x_total_hr_cost:
            profitability_items['costs']['data'].append({
                'id': 'custom_hr_costs',
                'sequence': sequence.get('custom_hr_costs', 50),
                'billed': -self.x_total_hr_cost,
                'to_bill': 0.0,
            })
            profitability_items['costs']['total']['billed'] -= self.x_total_hr_cost

        # Add Facilities Costs
        if self.x_facilities_cost:
            profitability_items['costs']['data'].append({
                'id': 'custom_facilities',
                'sequence': sequence.get('custom_facilities', 51),
                'billed': -self.x_facilities_cost,
                'to_bill': 0.0,
            })
            profitability_items['costs']['total']['billed'] -= self.x_facilities_cost

        # Add Travel & Lodging
        if self.x_travel_lodging:
            profitability_items['costs']['data'].append({
                'id': 'custom_travel',
                'sequence': sequence.get('custom_travel', 52),
                'billed': -self.x_travel_lodging,
                'to_bill': 0.0,
            })
            profitability_items['costs']['total']['billed'] -= self.x_travel_lodging

        # Add Other Costs
        if self.x_other_costs:
            profitability_items['costs']['data'].append({
                'id': 'custom_other',
                'sequence': sequence.get('custom_other', 53),
                'billed': -self.x_other_costs,
                'to_bill': 0.0,
            })
            profitability_items['costs']['total']['billed'] -= self.x_other_costs

        # Add custom revenue if we have net value from sale orders
        if self.x_net_value and not any(r.get('id') == 'custom_revenue' for r in profitability_items['revenues']['data']):
            # Check if there's already revenue data, if not add our custom one
            existing_revenue = profitability_items['revenues']['total']['invoiced'] + profitability_items['revenues']['total']['to_invoice']
            if existing_revenue == 0:
                profitability_items['revenues']['data'].append({
                    'id': 'custom_revenue',
                    'sequence': 1,
                    'invoiced': self.x_net_value,
                    'to_invoice': 0.0,
                })
                profitability_items['revenues']['total']['invoiced'] += self.x_net_value

        return profitability_items

    def _get_sale_order_lines(self):
        """Get sale order lines for the project."""
        sale_orders = self._get_sale_orders()
        return self.env['sale.order.line'].search([
            ('order_id', 'in', sale_orders.ids), 
            ('is_service', '=', True), 
            ('is_downpayment', '=', False)
        ], order='id asc')

    def _get_sold_items(self):
        """
        Get sold items data for Contract Terms section.
        Ported from Odoo 15 sale_timesheet module.
        Returns data structure for displaying WP items with hours.
        """
        timesheet_encode_uom = self.env.company.timesheet_encode_uom_id
        product_uom_unit = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        product_uom_hour = self.env.ref('uom.product_uom_hour', raise_if_not_found=False)

        sols = self._get_sale_order_lines()
        number_sale_orders = len(sols.order_id)
        
        sold_items = {
            'allow_billable': self.allow_billable if hasattr(self, 'allow_billable') else True,
            'data': [],
            'number_sols': len(sols),
            'total_sold': 0,
            'effective_sold': 0,
            'company_unit_name': timesheet_encode_uom.name if timesheet_encode_uom else 'Hours'
        }

        for sol in sols:
            # Get display name
            if number_sale_orders > 1:
                name = sol.display_name
            else:
                name = sol.name

            product_uom_convert = sol.product_uom
            if product_uom_unit and product_uom_convert == product_uom_unit:
                product_uom_convert = product_uom_hour

            # Calculate quantities
            qty_delivered = 0.0
            product_uom_qty = 0.0
            
            if product_uom_convert and timesheet_encode_uom:
                try:
                    qty_delivered = product_uom_convert._compute_quantity(
                        sol.qty_delivered, timesheet_encode_uom, raise_if_failure=False
                    ) or 0.0
                    product_uom_qty = product_uom_convert._compute_quantity(
                        sol.product_uom_qty, timesheet_encode_uom, raise_if_failure=False
                    ) or 0.0
                except Exception:
                    qty_delivered = sol.qty_delivered or 0.0
                    product_uom_qty = sol.product_uom_qty or 0.0

                if product_uom_convert.category_id == timesheet_encode_uom.category_id:
                    product_uom_convert = timesheet_encode_uom

            if qty_delivered > 0 or product_uom_qty > 0:
                uom_name = product_uom_convert.name if product_uom_convert else 'Hours'
                sold_items['data'].append({
                    'name': name,
                    'value': '%s / %s %s' % (
                        formatLang(self.env, qty_delivered, digits=1),
                        formatLang(self.env, product_uom_qty, digits=1),
                        uom_name
                    ),
                    'color': 'red' if qty_delivered > product_uom_qty else 'black'
                })
                
                # Sum totals for time-based products
                if timesheet_encode_uom and product_uom_unit:
                    if (sol.product_uom.category_id == timesheet_encode_uom.category_id or 
                        (sol.product_uom == product_uom_unit and 
                         hasattr(sol.product_id, 'service_policy') and 
                         sol.product_id.service_policy != 'delivered_manual')):
                        sold_items['total_sold'] += product_uom_qty
                        sold_items['effective_sold'] += qty_delivered

        remaining = sold_items['total_sold'] - sold_items['effective_sold']
        sold_items['remaining'] = {
            'value': remaining,
            'color': 'red' if remaining < 0 else 'black',
        }
        
        # Check if forecast is available
        sold_items['allow_forecast'] = hasattr(self, 'allow_forecast') and self.allow_forecast
        sold_items['planned_sold'] = 0  # Placeholder for forecast data
        
        return sold_items

    def _get_custom_profitability_items(self):
        """
        Get custom profitability items in the format expected by the old template.
        Returns data in the format: [{'name': 'Label', 'value': 'formatted_value', 'color': 'color'}]
        """
        currency = self.company_id.currency_id
        items = []
        
        # Force recomputation
        self._compute_profitability_metrics()
        
        # Untaxed Amount
        items.append({
            'name': 'Untaxed Amount',
            'value': format_amount(self.env, self.x_net_value or 0.0, currency),
            'color': ''
        })
        
        # HR Costs
        items.append({
            'name': 'HR Costs',
            'value': format_amount(self.env, -(self.x_total_hr_cost or 0.0), currency),
            'color': 'red' if self.x_total_hr_cost else ''
        })
        
        # Facilities Costs
        items.append({
            'name': 'Facilities Costs',
            'value': format_amount(self.env, -(self.x_facilities_cost or 0.0), currency),
            'color': 'red' if self.x_facilities_cost else ''
        })
        
        # Travel & Lodging
        items.append({
            'name': 'Travel & Lodging',
            'value': format_amount(self.env, -(self.x_travel_lodging or 0.0), currency),
            'color': 'red' if self.x_travel_lodging else ''
        })
        
        # Other Costs
        items.append({
            'name': 'Other Costs',
            'value': format_amount(self.env, -(self.x_other_costs or 0.0), currency),
            'color': 'red' if self.x_other_costs else ''
        })
        
        # Margin
        items.append({
            'name': 'Margin',
            'value': format_amount(self.env, self.x_final_margin or 0.0, currency),
            'color': 'green' if (self.x_final_margin or 0) >= 0 else 'red'
        })
        
        # Taxes
        items.append({
            'name': 'Taxes',
            'value': format_amount(self.env, self.x_total_taxes or 0.0, currency),
            'color': 'yellow' if self.x_total_taxes else ''
        })
        
        return items

    def get_panel_data(self):
        """
        Extend the project panel data to include additional profitability information.
        Includes: HR cost button, sold_items (Contract Terms), and profitability_items.
        """
        self.ensure_one()
        data = super().get_panel_data()
        
        if not data:
            return data
            
        # Force recomputation to ensure up-to-date values
        self._compute_profitability_metrics()

        # Add custom button for Summary of HR Costs
        if 'buttons' in data:
            data['buttons'].append({
                'icon': 'money',
                'text': self.env._('HR Costs Detail'),
                'number': format_amount(self.env, self.x_total_hr_cost or 0.0, self.company_id.currency_id),
                'action_type': 'object',
                'action': 'action_open_payment_report',
                'additional_context': json.dumps({'default_project_id': self.id}),
                'show': True,
                'sequence': 45,
            })
            
        # Add HR cost warning to the data if exists
        if self.x_hr_cost_warning:
            data['hr_cost_warning'] = self.x_hr_cost_warning

        # Add sold_items for Contract Terms section (like Odoo 15)
        data['sold_items'] = self._get_sold_items()
        
        # Add analytic_account_id for profitability check
        if hasattr(self, 'analytic_account_id'):
            data['analytic_account_id'] = self.analytic_account_id.id if self.analytic_account_id else False
        elif hasattr(self, 'account_id'):
            data['analytic_account_id'] = self.account_id.id if self.account_id else False
        else:
            data['analytic_account_id'] = False

        # Add custom profitability items in old format for our custom template
        data['custom_profitability_items'] = {
            'data': self._get_custom_profitability_items()
        }

        return data

    def _get_stat_buttons(self):
        """
        Override to add/modify stat buttons.
        Odoo 18 uses 'sequence' for ordering buttons.
        """
        buttons = super()._get_stat_buttons()
        
        # Optionally modify existing buttons or add new ones here
        # For example, rename 'Gross Margin' if it exists
        for button in buttons:
            if button.get('text') == 'Gross Margin':
                button['text'] = self.env._('Detailed HR Costs')
                button['number'] = format_amount(
                    self.env, 
                    self.x_total_hr_cost or 0.0, 
                    self.company_id.currency_id
                )
        
        return buttons

    def _get_sale_orders(self):
        """
        Override to include both sale order lines and direct sale orders.
        This ensures projects linked directly to sale orders (not just via sale lines) are included.
        """
        sale_orders = super()._get_sale_orders()
        # Also include direct sale order connections
        if self.sale_order_id:
            sale_orders |= self.sale_order_id
        
        # Additional fallback: search by project name if no direct links found
        if not sale_orders:
            sale_orders = self.env['sale.order'].search([('name', '=', self.name)], limit=1)
        
        return sale_orders

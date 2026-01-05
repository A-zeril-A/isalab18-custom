# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class CustomProjectProfitabilityDashboard(models.TransientModel):
    """
    Transient model for generating and displaying the Project Profitability Dashboard.
    Integrates HR cost, facilities, taxes, and margin analysis for each project.
    
    This model creates temporary report lines for viewing HR costs breakdown per user.
    Each line shows:
    - User/Employee who logged timesheets
    - Total hours worked
    - Hourly rate (from employee settings)
    - Total cost (hours × rate)
    """
    _name = 'custom.project.profitability.dashboard'
    _description = 'Custom Project Profitability Dashboard'

    user_id = fields.Many2one('res.users', string='User')
    employee_id = fields.Many2one(
        'hr.employee', 
        string='Employee', 
        compute='_compute_employee', 
        store=True
    )
    total_hours = fields.Float(string='Total Hours')
    hourly_rate = fields.Float(string='Hourly Rate')
    total_payment = fields.Float(
        string='Total Payment', 
        compute='_compute_total_payment', 
        store=True
    )
    project_id = fields.Many2one('project.project', string='Project')

    @api.depends('user_id')
    def _compute_employee(self):
        """Compute the employee linked to the user."""
        for rec in self:
            rec.employee_id = rec.user_id.employee_id if rec.user_id else False

    @api.depends('total_hours', 'hourly_rate')
    def _compute_total_payment(self):
        """
        Compute the total payment by multiplying total hours with hourly rate.
        """
        for rec in self:
            hours = rec.total_hours or 0.0
            rate = rec.hourly_rate or 0.0
            rec.total_payment = hours * rate

    @api.model
    def generate_report_lines(self, project_id):
        """
        Generate dashboard lines for the profitability report based on timesheet data.
        Calculates total hours and retrieves the hourly rate from the employee's hourly_cost.
        
        Args:
            project_id: The ID of the project to generate report for
            
        Returns:
            True on success
        """
        if not project_id:
            return False
            
        domain = [('project_id', '=', project_id)]

        # Group timesheet entries by user and sum their worked hours (unit_amount).
        data = self.env['account.analytic.line'].read_group(
            domain,
            ['user_id', 'unit_amount:sum'],
            ['user_id']
        )

        # Remove previous report lines for this project to avoid duplicates.
        existing_lines = self.search([('project_id', '=', project_id)])
        existing_lines.unlink()

        # Get all users from the data
        user_ids = [d['user_id'][0] for d in data if d['user_id']]
        users = self.env['res.users'].browse(user_ids)
        
        # Retrieve hourly rates from the employee's 'hourly_cost' field
        # In Odoo 16+, 'timesheet_cost' was renamed to 'hourly_cost'
        rates = {}
        for user in users:
            if user.employee_id:
                rates[user.id] = user.employee_id.hourly_cost or 0
            else:
                rates[user.id] = 0
                _logger.warning(
                    "User %s (ID: %s) has no linked employee. HR cost will be 0.",
                    user.name, user.id
                )

        # Create report lines with the calculated total hours and hourly rates.
        lines_to_create = []
        for line in data:
            if not line['user_id']:
                continue
            user_id = line['user_id'][0]
            hours = line['unit_amount'] or 0.0
            rate = rates.get(user_id, 0)
            lines_to_create.append({
                'user_id': user_id,
                'total_hours': hours,
                'hourly_rate': rate,
                'project_id': project_id,
            })
        
        # Batch create for better performance
        if lines_to_create:
            self.create(lines_to_create)

        return True

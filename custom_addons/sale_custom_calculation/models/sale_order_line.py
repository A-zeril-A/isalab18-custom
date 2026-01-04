# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Custom field for manual subtotal entry
    manual_price_subtotal = fields.Float(
        string='Manual Subtotal',
        digits='Product Price',
        compute='_compute_manual_subtotal',
        inverse='_inverse_manual_subtotal',
        store=True,
        help='Editable subtotal field that allows reverse calculation of unit price'
    )

    @api.depends('product_uom_qty', 'price_unit')
    def _compute_manual_subtotal(self):
        """Compute subtotal based on quantity and unit price."""
        for line in self:
            line.manual_price_subtotal = line.product_uom_qty * line.price_unit

    def _inverse_manual_subtotal(self):
        """Calculate unit price when user enters subtotal manually."""
        for line in self:
            if line.product_uom_qty and line.manual_price_subtotal:
                if line.product_uom_qty <= 0:
                    raise UserError("Quantity must be greater than zero!")
                line.price_unit = line.manual_price_subtotal / line.product_uom_qty

    @api.onchange('product_id')
    def _onchange_product_id_custom(self):
        """Set default price when product changes."""
        if self.product_id:
            self.price_unit = self.product_id.list_price

    @api.onchange('product_uom_qty', 'price_unit')
    def _onchange_qty_price(self):
        """Update subtotal when quantity or unit price changes."""
        if self.product_uom_qty and self.price_unit:
            self.manual_price_subtotal = self.product_uom_qty * self.price_unit

    @api.onchange('manual_price_subtotal')
    def _onchange_manual_subtotal(self):
        """Recalculate unit price when user changes subtotal directly."""
        if self.product_uom_qty and self.manual_price_subtotal:
            if self.product_uom_qty <= 0:
                raise UserError("Quantity must be greater than zero!")
            self.price_unit = self.manual_price_subtotal / self.product_uom_qty

    def write(self, vals):
        """Handle calculations during record save."""
        if 'manual_price_subtotal' in vals and 'product_uom_qty' in vals:
            if vals.get('product_uom_qty') and vals.get('manual_price_subtotal'):
                if vals['product_uom_qty'] <= 0:
                    raise UserError("Quantity must be greater than zero!")
                vals['price_unit'] = vals['manual_price_subtotal'] / vals['product_uom_qty']
        
        elif 'manual_price_subtotal' in vals:
            # Only subtotal changed
            for line in self:
                if line.product_uom_qty and vals.get('manual_price_subtotal'):
                    if line.product_uom_qty <= 0:
                        raise UserError("Quantity must be greater than zero!")
                    vals['price_unit'] = vals['manual_price_subtotal'] / line.product_uom_qty
        
        return super(SaleOrderLine, self).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """Handle calculations during record creation."""
        for vals in vals_list:
            if vals.get('manual_price_subtotal') and vals.get('product_uom_qty'):
                if vals['product_uom_qty'] <= 0:
                    raise UserError("Quantity must be greater than zero!")
                vals['price_unit'] = vals['manual_price_subtotal'] / vals['product_uom_qty']
        
        return super(SaleOrderLine, self).create(vals_list)
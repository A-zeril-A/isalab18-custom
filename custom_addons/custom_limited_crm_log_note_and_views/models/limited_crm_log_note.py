# -*- coding: utf-8 -*-
from odoo import models, api, fields


class CrmLead(models.Model):
    _inherit = "crm.lead"

    # Computed field to check if user can see financial information
    can_see_financials = fields.Boolean(
        compute="_compute_can_see_financials",
        store=False,
        compute_sudo=True,
    )

    def _compute_can_see_financials(self):
        """
        Determine if the current user has permission to view financial fields.
        This is based on group membership, not on the record's user_id.
        """
        has_access = self.env.user.has_group(
            'custom_limited_crm_log_note_and_views.group_crm_full_access'
        )
        for record in self:
            record.can_see_financials = has_access

    @api.model
    def _track_get_fields(self):
        """
        Override to limit which fields are tracked in the chatter.
        Only partner_id changes will be logged, filtering out other
        tracked fields like stage_id, expected_revenue, etc.
        
        This reduces chatter noise by only showing customer-related changes.
        """
        # Get all tracked fields from parent
        all_tracked_fields = super()._track_get_fields()
        
        # Only keep partner_id for tracking
        # Returns a set of field names that should be tracked
        if all_tracked_fields:
            return all_tracked_fields & {'partner_id'}
        return set()

    def _track_subtype(self, init_values):
        """
        Override to customize tracking subtypes.
        Returns appropriate subtype when partner_id changes.
        """
        self.ensure_one()
        if 'partner_id' in init_values:
            return self.env.ref('crm.mt_lead_stage')
        return super()._track_subtype(init_values)

    def _track_get_default_log_message(self, tracked_fields):
        """
        Customize the default log message for tracking.
        Shows opportunity name and customer name in tracked changes.
        """
        self.ensure_one()
        # Only provide custom message if partner_id changed
        if 'partner_id' in tracked_fields:
            message = f"Opportunity: {self.name}"
            if self.partner_id:
                message += f" - Customer: {self.partner_id.name}"
            return message
        return super()._track_get_default_log_message(tracked_fields)

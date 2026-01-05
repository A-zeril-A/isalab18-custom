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
        
        Only partner_id and stage_id changes will be logged:
        - partner_id: Customer changes (our custom requirement)
        - stage_id: Required by mail.tracking.duration.mixin for duration tracking
        
        Other fields like expected_revenue, user_id, etc. will NOT be tracked,
        reducing chatter noise.
        """
        # Get all tracked fields from parent
        all_tracked_fields = super()._track_get_fields()
        
        if not all_tracked_fields:
            return set()
        
        # Keep only partner_id and stage_id for tracking
        # stage_id MUST be included because crm.lead uses mail.tracking.duration.mixin
        # which requires stage_id to have tracking=True for duration computation
        allowed_fields = {'partner_id', 'stage_id'}
        return all_tracked_fields & allowed_fields

    def _track_subtype(self, init_values):
        """
        Override to customize tracking subtypes.
        Returns appropriate subtype when tracked fields change.
        """
        self.ensure_one()
        # Use stage subtype for both partner and stage changes
        if 'partner_id' in init_values or 'stage_id' in init_values:
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

# -*- coding: utf-8 -*-
# Copyright 2026 - ISALab Migration Scripts
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

"""
End-migration script for Odoo 18 base module.
Handles cleanup of orphaned models, views, and data after migration.
"""

import logging

_logger = logging.getLogger(__name__)


def _cleanup_orphaned_models(cr):
    """
    Remove orphaned model declarations that reference non-existent modules.
    These cause 'cannot be loaded' warnings during startup.
    """
    orphaned_models = [
        'website.editor.unsanitize.html.field',
        'account.unreconcile',
        'account.tour.upload.bill',
    ]
    
    _logger.info("Cleaning up orphaned model declarations...")
    
    for model_name in orphaned_models:
        # Check if model exists in ir_model
        cr.execute("""
            SELECT id FROM ir_model WHERE model = %s
        """, (model_name,))
        result = cr.fetchone()
        
        if result:
            model_id = result[0]
            _logger.info("  Removing orphaned model: %s (id=%s)", model_name, model_id)
            
            # Delete related ir_model_data entries first
            cr.execute("""
                DELETE FROM ir_model_data 
                WHERE model = 'ir.model' AND res_id = %s
            """, (model_id,))
            
            # Delete model fields
            cr.execute("""
                DELETE FROM ir_model_fields WHERE model_id = %s
            """, (model_id,))
            
            # Delete the model itself
            cr.execute("""
                DELETE FROM ir_model WHERE id = %s
            """, (model_id,))
            
            _logger.info("    Model %s removed successfully", model_name)
        else:
            _logger.info("  Model %s not found (already clean)", model_name)


def _cleanup_orphaned_module_data(cr):
    """
    Remove ir_model_data entries for modules that were uninstalled.
    """
    uninstalled_modules = [
        'l10n_it_edi_sdicoop',
        'web_clipboard_fix',
        'website_editor_unsanitize_html_field',
    ]
    
    _logger.info("Cleaning up orphaned module data...")
    
    for module_name in uninstalled_modules:
        cr.execute("""
            SELECT COUNT(*) FROM ir_model_data WHERE module = %s
        """, (module_name,))
        count = cr.fetchone()[0]
        
        if count > 0:
            _logger.info("  Removing %d ir_model_data entries for module: %s", count, module_name)
            cr.execute("""
                DELETE FROM ir_model_data WHERE module = %s
            """, (module_name,))
        else:
            _logger.info("  Module %s has no orphaned data", module_name)


def _fix_account_edi_proxy_null_columns(cr):
    """
    Fix NULL values in account_edi_proxy_client_user table that prevent NOT NULL constraint.
    """
    _logger.info("Checking account_edi_proxy_client_user for NULL values...")
    
    # Check if table exists
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'account_edi_proxy_client_user'
        )
    """)
    if not cr.fetchone()[0]:
        _logger.info("  Table account_edi_proxy_client_user does not exist, skipping")
        return
    
    # Check for NULL values
    cr.execute("""
        SELECT COUNT(*) FROM account_edi_proxy_client_user 
        WHERE private_key_id IS NULL OR proxy_type IS NULL
    """)
    null_count = cr.fetchone()[0]
    
    if null_count > 0:
        _logger.info("  Found %d records with NULL values, removing them...", null_count)
        cr.execute("""
            DELETE FROM account_edi_proxy_client_user 
            WHERE private_key_id IS NULL OR proxy_type IS NULL
        """)
        _logger.info("  Removed %d invalid records", null_count)
    else:
        _logger.info("  No NULL values found")


def _deactivate_broken_views(cr):
    """
    Deactivate views that reference non-existent fields.
    The customer_information_contacts module has views referencing team_id 
    which doesn't exist in res.partner in Odoo 18.
    """
    broken_views = [
        # (xml_id, reason)
        ('customer_information_contacts.view_res_partner_form_extension', 
         "References team_id field that doesn't exist in res.partner"),
    ]
    
    _logger.info("Checking for broken views to deactivate...")
    
    for xml_id, reason in broken_views:
        parts = xml_id.split('.')
        if len(parts) != 2:
            continue
        module, name = parts
        
        cr.execute("""
            SELECT v.id, v.name, v.active 
            FROM ir_ui_view v
            JOIN ir_model_data d ON d.res_id = v.id AND d.model = 'ir.ui.view'
            WHERE d.module = %s AND d.name = %s
        """, (module, name))
        result = cr.fetchone()
        
        if result:
            view_id, view_name, is_active = result
            if is_active:
                _logger.info("  Deactivating view: %s (id=%s)", xml_id, view_id)
                _logger.info("    Reason: %s", reason)
                cr.execute("""
                    UPDATE ir_ui_view SET active = FALSE WHERE id = %s
                """, (view_id,))
            else:
                _logger.info("  View %s already inactive", xml_id)
        else:
            _logger.info("  View %s not found", xml_id)


def migrate(cr, version):
    """
    End-migration entry point for base module.
    Called by OpenUpgrade after all standard migration scripts complete.
    """
    _logger.info("base: end-migration script called with version %s", version)
    
    # Cleanup 1: Remove orphaned model declarations
    _cleanup_orphaned_models(cr)
    
    # Cleanup 2: Remove orphaned ir_model_data entries
    _cleanup_orphaned_module_data(cr)
    
    # Cleanup 3: Fix NULL values that prevent NOT NULL constraints
    _fix_account_edi_proxy_null_columns(cr)
    
    # Cleanup 4: Deactivate broken views
    _deactivate_broken_views(cr)
    
    _logger.info("base: end-migration completed successfully")


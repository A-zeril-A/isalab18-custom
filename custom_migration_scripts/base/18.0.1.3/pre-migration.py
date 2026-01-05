# -*- coding: utf-8 -*-
# Copyright 2026 - ISALab Migration Scripts
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

"""
Pre-migration script for Odoo 18 base module.
Handles cleanup of modules that are no longer installable or have inconsistent states.
"""

import logging

_logger = logging.getLogger(__name__)


def _uninstall_deprecated_modules(cr):
    """
    Mark deprecated/unavailable modules as uninstalled to prevent
    'inconsistent states' errors during Odoo startup.
    
    These modules either:
    - Were merged into other modules
    - Are no longer available in Odoo 18
    - Have installable: False in their manifest
    """
    deprecated_modules = [
        'l10n_it_edi_sdicoop',           # Merged into l10n_it_edi in Odoo 16+
        'web_clipboard_fix',              # No longer needed in Odoo 18
        'website_editor_unsanitize_html_field',  # installable: False
    ]
    
    _logger.info("Checking for deprecated modules to uninstall...")
    
    for module_name in deprecated_modules:
        cr.execute("""
            SELECT id, state FROM ir_module_module 
            WHERE name = %s
        """, (module_name,))
        result = cr.fetchone()
        
        if result:
            module_id, current_state = result
            if current_state != 'uninstalled':
                _logger.info(
                    "  Module '%s' (id=%s) state='%s' -> setting to 'uninstalled'",
                    module_name, module_id, current_state
                )
                cr.execute("""
                    UPDATE ir_module_module 
                    SET state = 'uninstalled' 
                    WHERE id = %s
                """, (module_id,))
            else:
                _logger.info("  Module '%s' already uninstalled.", module_name)
        else:
            _logger.info("  Module '%s' not found in database.", module_name)


def _remove_unavailable_modules_completely(cr):
    """
    Completely remove modules that have no code available.
    This prevents Odoo from trying to load them and changing their state.
    """
    modules_to_remove = [
        'web_clipboard_fix',  # Code not available in Odoo 18
    ]
    
    _logger.info("Removing unavailable modules completely from database...")
    
    for module_name in modules_to_remove:
        cr.execute("""
            SELECT id FROM ir_module_module WHERE name = %s
        """, (module_name,))
        result = cr.fetchone()
        
        if result:
            module_id = result[0]
            _logger.info("  Removing module '%s' (id=%s) completely...", module_name, module_id)
            
            # Remove module dependencies
            cr.execute("""
                DELETE FROM ir_module_module_dependency 
                WHERE module_id = %s OR name = %s
            """, (module_id, module_name))
            if cr.rowcount > 0:
                _logger.info("    Removed %s dependency records", cr.rowcount)
            
            # Remove ir.model.data for the module record itself
            cr.execute("""
                DELETE FROM ir_model_data 
                WHERE model = 'ir.module.module' AND res_id = %s
            """, (module_id,))
            if cr.rowcount > 0:
                _logger.info("    Removed ir.model.data for module record")
            
            # Remove the module record
            cr.execute("""
                DELETE FROM ir_module_module WHERE id = %s
            """, (module_id,))
            _logger.info("    Module '%s' removed from ir_module_module", module_name)
        else:
            _logger.info("  Module '%s' not found in database.", module_name)


def migrate(cr, version):
    """
    Pre-migration entry point for base module.
    Called by OpenUpgrade before the standard migration scripts.
    """
    _logger.info("base: pre-migration script called with version %s", version)
    
    # Fix 1: Uninstall deprecated/unavailable modules
    _uninstall_deprecated_modules(cr)
    
    # Fix 2: Completely remove modules that have no code available
    _remove_unavailable_modules_completely(cr)
    
    _logger.info("base: pre-migration completed successfully")


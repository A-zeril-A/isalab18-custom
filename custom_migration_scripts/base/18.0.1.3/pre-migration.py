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
            WHERE name = %s AND state != 'uninstalled'
        """, (module_name,))
        result = cr.fetchone()
        
        if result:
            module_id, current_state = result
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
            _logger.info("  Module '%s' already uninstalled or not found.", module_name)


def migrate(cr, version):
    """
    Pre-migration entry point for base module.
    Called by OpenUpgrade before the standard migration scripts.
    """
    _logger.info("base: pre-migration script called with version %s", version)
    
    # Fix 1: Uninstall deprecated/unavailable modules
    _uninstall_deprecated_modules(cr)
    
    _logger.info("base: pre-migration completed successfully")


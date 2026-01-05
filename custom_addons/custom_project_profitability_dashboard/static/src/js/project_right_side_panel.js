/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProjectRightSidePanel } from "@project/components/project_right_side_panel/project_right_side_panel";

/**
 * Patch the ProjectRightSidePanel to add custom sections:
 * - Contract Terms (sold_items / WP items)
 * - Project's Time Performance
 * - Project Financial Performance
 * 
 * The data for these sections is provided by the Python get_panel_data override.
 */
patch(ProjectRightSidePanel.prototype, {
    /**
     * Override panelVisible to show panel when sold_items or custom profitability data exists
     */
    get panelVisible() {
        const hasSoldItems = this.state.data.sold_items && 
                            this.state.data.sold_items.number_sols > 0 &&
                            this.state.data.sold_items.allow_billable;
        const hasCustomProfitability = this.state.data.custom_profitability_items && 
                                       this.state.data.custom_profitability_items.data &&
                                       this.state.data.custom_profitability_items.data.length > 0;
        return super.panelVisible || hasSoldItems || hasCustomProfitability;
    },

    /**
     * Check if sold items section should be shown
     */
    get showSoldItems() {
        return this.state.data.sold_items && 
               this.state.data.sold_items.number_sols > 0 &&
               this.state.data.sold_items.allow_billable;
    },

    /**
     * Check if custom profitability section should be shown
     */
    get showCustomProfitability() {
        return this.state.data.custom_profitability_items && 
               this.state.data.custom_profitability_items.data &&
               this.state.data.custom_profitability_items.data.length > 0 &&
               this.state.data.analytic_account_id;
    },

    /**
     * Get HR cost warning message if exists
     */
    get hrCostWarning() {
        return this.state.data.hr_cost_warning || false;
    },
});

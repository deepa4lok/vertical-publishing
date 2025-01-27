# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class SaleOrderConfirm(models.TransientModel):
    """
    This wizard will confirm the all the selected draft invoices
    """

    _name = "sale.order.confirm"
    _description = "Confirm the selected sale orders"

    
    def sale_order_confirm(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for record in self.env['sale.order'].browse(active_ids):
            if record.state not in ('draft', 'proforma', 'proforma2'):
                raise UserError(_("Selected order(s) cannot be confirmed as they are not in 'Draft', 'Approved' or 'Sent' state."))
            record.action_confirm()
        return {'type': 'ir.actions.act_window_close'}


'''class AccountInvoiceCancel(models.TransientModel):
    """
    This wizard will cancel the all the selected invoices.
    If in the journal, the option allow cancelling entry is not selected then it will give warning message.
    """

    _name = "account.invoice.cancel"
    _description = "Cancel the Selected Invoices"

    
    def invoice_cancel(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for record in self.env['account.invoice'].browse(active_ids):
            if record.state in ('cancel', 'paid'):
                raise UserError(_("Selected invoice(s) cannot be cancelled as they are already in 'Cancelled' or 'Done' state."))
            record.action_invoice_cancel()
        return {'type': 'ir.actions.act_window_close'}'''

# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    
    def _prepare_invoice_values(self, order, name, amount, so_line):
        invoice_vals = super(SaleAdvancePaymentInv, self)._prepare_invoice_values(order, name, amount, so_line)
        if order.invoicing_date:
            invoice_vals['invoice_date'] = order.invoicing_date
        return invoice_vals
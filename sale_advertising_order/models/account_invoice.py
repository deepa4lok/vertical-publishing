# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016 Magnus NL (<http://magnus.nl>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from odoo import api, fields, models, _



class Invoice(models.Model):
    """ Inherits invoice and adds hon boolean to invoice to flag hon-invoices"""
    _inherit = 'account.invoice'


    ad = fields.Boolean('Ad', help="It indicates that the invoice is a Advertising Invoice.", default=False)


    @api.multi
    def invoice_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.ensure_one()
        self.sent = True

        if self.hon == True:
            return self.env['report'].get_action(self, 'account.invoice.hon')

        return super(Invoice, self).invoice_print()


    @api.multi
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()

        if self.hon:
            template = self.env.ref('freelancer_self_billing.email_template_hon_invoice', False)
            custom_layout = False
        else:
            template = self.env.ref('account.email_template_edi_invoice', False)
            custom_layout = "account.mail_template_data_notification_email_account_invoice"

        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)

        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout=custom_layout,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }


class InvoiceLine(models.Model):
    """ Inherits invoice.line and adds activity from analytic_secondaxis to invoice """
    _inherit = 'account.invoice.line'


    ad_order_line_id = fields.Many2one('sale.order.line', 'Advertising Order Line')
    date_publish = fields.Date('Publishing Date')
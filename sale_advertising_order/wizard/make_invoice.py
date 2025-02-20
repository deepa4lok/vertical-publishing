# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from unidecode import unidecode


class AdOrderMakeInvoice(models.TransientModel):
    _name = "ad.order.make.invoice"
    _description = "Advertising Order Make_invoice"

    invoice_date = fields.Date(default=fields.Date.today)
    posting_date = fields.Date(default=False)

    def make_invoices_from_ad_orders(self):
        context = self._context

        order_ids = context.get("active_ids", [])
        his_obj = self.env["ad.order.line.make.invoice"]
        lines = self.env["sale.order.line"].search([("order_id", "in", order_ids)])
        ctx = context.copy()
        ctx["active_ids"] = lines.ids
        ctx["invoice_date"] = self.invoice_date
        ctx["posting_date"] = (
            self.posting_date and self.posting_date or self.invoice_date
        )
        his_obj.with_context(**ctx).make_invoices_from_lines()
        return True


class AdOrderLineMakeInvoice(models.TransientModel):
    _name = "ad.order.line.make.invoice"
    _description = "Advertising Order Line Make_invoice"

    invoice_date = fields.Date(default=fields.Date.today)
    posting_date = fields.Date(default=False)

    @api.model
    def _prepare_invoice(self, keydict, lines, invoice_date, posting_date):
        ref = self.env.ref
        partner = keydict["partner_id"]
        currency = (
            keydict.get("currency") or partner.property_product_pricelist.currency_id
        )
        published_customer = keydict["published_customer"]
        payment_mode = keydict["payment_mode_id"]
        customer_contact = keydict["customer_contact_id"]
        invoice_payment_term_id = keydict["payment_term_id"]
        vals = {
            "invoice_date": invoice_date,
            "date": posting_date or False,
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "published_customer": published_customer.id,
            "customer_contact": customer_contact,
            "invoice_line_ids": lines["lines"],
            # 'narration': lines['name'], # ??
            "invoice_payment_term_id": invoice_payment_term_id,
            # 'journal_id': self.company_data['default_journal_sale'].id, # FIXME
            "fiscal_position_id": partner.property_account_position_id.id or False,
            "user_id": self.env.user.id,
            "company_id": keydict["company_id"],
            "payment_mode_id": payment_mode.id or False,
            "partner_bank_id": payment_mode.fixed_journal_id.bank_account_id.id
            if payment_mode.bank_account_link == "fixed"
            else partner.bank_ids and partner.bank_ids[0].id or False,
            "sale_type_id": ref("sale_advertising_order.ads_sale_type").id,
            "ref": keydict["client_order_ref"],
            "currency_id": currency.id,
        }
        return vals

    def make_invoices_from_lines(self):
        """
        To make invoices.
        """
        context = self._context
        inv_date = self.invoice_date
        post_date = self.posting_date

        if not context.get("active_ids", []):
            message = "No ad order lines selected for invoicing."
            raise UserError(_(message))
        else:
            lids = context.get("active_ids", [])
            OrderLines = self.env["sale.order.line"].browse(lids)
            invoice_date_ctx = context.get("invoice_date", False)
            posting_date_ctx = context.get("posting_date", False)
        if invoice_date_ctx and not inv_date:
            inv_date = invoice_date_ctx
        if posting_date_ctx and not post_date:
            post_date = posting_date_ctx

        if not post_date:
            post_date = inv_date  # Enforce Inv Date
        self.make_invoices_job_queue(inv_date, post_date, OrderLines)
        return "Lines dispatched."

    def modify_key(self, key, keydict, line):
        """Hook method to modify grouping key of advertising invoicing"""
        key = list(key)
        key.append(line.order_id.customer_contact)
        key = tuple(key)
        keydict["customer_contact_id"] = line.order_id.customer_contact.id
        return key, keydict

    def make_invoice(self, keydict, lines, inv_date, post_date):
        vals = self._prepare_invoice(keydict, lines, inv_date, post_date)
        invoice = self.env["account.move"].create(vals)
        return invoice

    # @job
    def make_invoices_job_queue(self, inv_date, post_date, chunk):
        invoices = {}
        count = 0
        for line in chunk:
            key = (
                line.order_id.partner_invoice_id,
                line.order_id.published_customer,
                line.order_id.payment_mode_id,
                line.order_id.payment_term_id,
                line.order_id.company_id.id,
            )
            keydict = {
                "partner_id": line.order_id.partner_invoice_id,
                "published_customer": line.order_id.published_customer,
                "payment_mode_id": line.order_id.payment_mode_id,
                "payment_term_id": line.order_id.payment_term_id.id,
                "company_id": line.order_id.company_id.id,
                "client_order_ref": line.order_id.client_order_ref,
                "currency": line.order_id.currency_id,
            }
            key, keydict = self.modify_key(key, keydict, line)

            if line.qty_to_invoice > 0 and (line.state in ("sale", "done")):
                if key not in invoices:
                    invoices[key] = {"lines": [], "name": ""}
                    invoices[key]["keydict"] = keydict
                inv_line_vals = self._prepare_invoice_line(line)
                invoices[key]["lines"].append((0, 0, inv_line_vals))
                if count < 3:
                    invoices[key]["name"] += unidecode(line.name) + " / "
                count += 1

        if not invoices:
            raise UserError(
                _(
                    "Invoice cannot be created for this Advertising Order Line "
                    "due to one of the following reasons:\n"
                    '1.The state of these ad order lines are not "sale" or "done"!\n'
                    "2.The Lines are already Invoiced!\n"
                )
            )

        for key, il in invoices.items():
            try:
                self.make_invoice(invoices[key]["keydict"], il, inv_date, post_date)
            except Exception as e:
                raise UserError(
                    _("The details of the error: '%(error)s' regarding '%(name)s'")
                    % {"error": str(e), "name": il["name"]}
                ) from e
        return "Invoice(s) successfully made."

    @api.model
    def open_invoices(self, invoice_ids):
        """open a view on one of the given invoice_ids"""

        action = self.env.ref("account.action_invoice_tree2").read()[0]
        if len(invoice_ids) > 1:
            action["domain"] = [("id", "in", invoice_ids)]
        elif len(invoice_ids) == 1:
            action["views"] = [(self.env.ref("account.invoice_form").id, "form")]
            action["res_id"] = invoice_ids[0]
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action

    def _prepare_invoice_line(self, line):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param line: sales order line to invoice
        """
        line.ensure_one()
        account = (
            line.product_id.property_account_income_id
            or line.product_id.categ_id.property_account_income_categ_id
        )
        if not account:
            raise UserError(
                _(
                    'Please define income account for this product: "%(name)s"'
                    '(id: %(id)d) - or for its category: "%(category)s".'
                )
                % {
                    "name": line.product_id.name,
                    "id": line.product_id.id,
                    "category": line.product_id.categ_id.name,
                }
            )

        fpos = (
            line.order_id.fiscal_position_id
            or line.order_id.partner_id.property_account_position_id
        )
        if fpos:
            account = fpos.map_account(account)

        return line._prepare_invoice_line(
            **{
                "name": line.title.name or "/",
                "account_id": account.id,
                # TODO: why not qty_to_invoice?
                "quantity": line.product_uom_qty,
                "analytic_tag_ids": [(6, 0, line.analytic_tag_ids.ids or [])],
            }
        )

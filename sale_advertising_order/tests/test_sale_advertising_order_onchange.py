from odoo.tests.common import Form, TransactionCase


class TestSaleAdvertisingOrderOnchange(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env['res.partner'].search([('is_customer', '=', True)], limit=1)
        cls.one_issue_product = cls.env.ref('sale_advertising_order.product_template_digital1')
        cls.multi_issue_product = cls.env.ref('sale_advertising_order.product_template_digital2')
        cls.order = cls.env['sale.order'].create({
            'advertising': True,
            'published_customer': cls.customer.id,
            'partner_id': cls.customer.id,
            'type_id': cls.env.ref('sale_advertising_order.ads_sale_type').id,
        })
        cls.order_view = cls.env.ref("sale_advertising_order.sale_order_view_form_sao")
        cls.product_template_digital1 = cls.env.ref('sale_advertising_order.product_template_digital1')
        cls.product_template_digital2 = cls.env.ref('sale_advertising_order.product_template_digital2')
        cls.product_category_main = cls.env.ref('sale_advertising_order.digital_advertising_category')
        cls.product_category_sub = cls.env.ref('sale_advertising_order.product_category_ads_digital1')
        cls.title1 = cls.env.ref('sale_advertising_order.title1')
        cls.title2 = cls.env.ref('sale_advertising_order.title2')
        cls.issue1 = cls.env.ref('sale_advertising_order.issue1')
        cls.issue2 = cls.env.ref('sale_advertising_order.issue2')
        cls.issue3 = cls.env.ref('sale_advertising_order.issue3')
        cls.discount_reason = cls.env.ref('sale_advertising_order.discount_reason1')

    def test_one_issue_onchange(self):
        with Form(self.order, self.order_view) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.medium = self.product_category_main
                self.assertEqual(line_form.ad_class, self.product_category_sub)

                line_form.title_ids.add(self.title1)
                self.assertEqual(len(line_form.adv_issue_ids), 1)
                self.assertIn(self.issue1, line_form.adv_issue_ids)
                self.assertEqual(line_form.multi_line, False)

                line_form.product_template_id = self.product_template_digital1
                self.assertEqual(line_form.actual_unit_price, 42)
                self.assertEqual(line_form.subtotal_before_agency_disc, 42)
                self.assertEqual(line_form.computed_discount, 0)

                line_form.subtotal_before_agency_disc = 21
                line_form.discount_reason_id = self.discount_reason
                self.assertEqual(line_form.computed_discount, 50)
                self.assertEqual(line_form.actual_unit_price, 21)

    def test_multi_issue_onchange(self):
        with Form(self.order, self.order_view) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.medium = self.product_category_main
                self.assertEqual(line_form.ad_class, self.product_category_sub)

                line_form.title_ids.add(self.title2)
                self.assertFalse(len(line_form.adv_issue_ids))

                line_form.adv_issue_ids.add(self.issue2)
                line_form.adv_issue_ids.add(self.issue3)
                self.assertEqual(line_form.multi_line, True)

                line_form.product_template_id = self.product_template_digital2
                self.assertEqual(line_form.comb_list_price, 8484)
                self.assertEqual(line_form.subtotal_before_agency_disc, 8484)
                self.assertEqual(line_form.computed_discount, 0)

                line_form.subtotal_before_agency_disc = 4242
                line_form.discount_reason_id = self.discount_reason
                self.assertEqual(line_form.computed_discount, 50)
                self.assertEqual(line_form.comb_list_price, 8484)

        # check that computed discount survives splitting multi line
        self.env['sale.order.line.create.multi.lines'].with_context(
            active_model=self.order._name, active_id=self.order.id, active_ids=self.order.ids,
        ).create_multi_lines(raise_exception=False)

        self.assertEqual(len(self.order.order_line), 2)
        self.assertEqual(self.order.order_line.mapped('computed_discount'), [50, 50])
        self.assertEqual(self.order.order_line.mapped('subtotal_before_agency_disc'), [2121, 2121])
        self.assertEqual(self.order.order_line.mapped('price_unit'), [4242, 4242])

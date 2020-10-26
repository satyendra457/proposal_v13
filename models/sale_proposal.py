# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.misc import formatLang, get_lang


class SaleProposal(models.Model):
    _name = 'sale.proposal'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Sale Proposal'


    @api.depends('proposal_line.subtotal_price_proposed')
    def _amount_proposed_all(self):
        """
        Compute the total amounts of the Proposal.
        """
        for proposal in self:
            amount_proposed = 0.0
            for line in proposal.proposal_line:
                amount_proposed += line.subtotal_price_proposed
            proposal.update({
                'amount_total_proposed': amount_proposed,
            })

    @api.depends('proposal_line.subtotal_price_accepted')
    def _amount_accepted_all(self):
        """
        Compute the total amounts of the Proposal.
        """
        for proposal in self:
            amount_accepted = 0.0
            for line in proposal.proposal_line:
                amount_accepted += line.subtotal_price_accepted
            proposal.update({
                'amount_total_accepted': amount_accepted,
            })

    #view related fields
    name = fields.Char(string='Proposal Reference', required=True, copy=False, readonly=True,
             states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    user_id = fields.Many2one(
        'res.users', string='Salesperson', index=True, tracking=2,
         default=lambda self: self.env.user,
        domain=lambda self: [('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman').id)])
    partner_id = fields.Many2one(
        'res.partner', string='Customer', readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        required=True, change_default=True, index=True, tracking=1,)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist',
        required=True, readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        help="If you change the pricelist, only newly added lines will be affected.")
    currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id',
                 string="Currency", readonly=True, required=True)
    is_proposal_accepted = fields.Boolean("Proposal Accepted")

    #Total Amount related Fields
    amount_total_proposed = fields.Monetary(string='Total Amount Proposed', store=True,
                 readonly=True, compute='_amount_proposed_all', tracking=4)
    amount_total_accepted = fields.Monetary(string='Total Amount Accepted', store=True,
                 readonly=True, compute='_amount_accepted_all', tracking=4)

    #One2many related fields
    proposal_line = fields.One2many('sale.proposal.line', 'sale_proposal_id', string='Proposal Lines',
                 states={'cancel': [('readonly', True)], 'sent': [('readonly', True)]},
                 copy=True, auto_join=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.proposal') or _('New')
        return super(SaleProposal, self).create(vals)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.pricelist_id = self.partner_id.property_product_pricelist and \
                         self.partner_id.property_product_pricelist.id or False,

    def proposal_send(self):
        mail_template = self.env.ref('proposal_v13.email_template_for_accept_proposal')
        if mail_template:
            mail_template.sudo().send_mail(self.id, force_send=True)
        self.state = 'sent'

    def proposal_confirm(self):
        self.create_contract()
        self.state = 'confirm'

    def _compute_access_url(self):
        super(SaleProposal, self)._compute_access_url()
        for proposal in self:
            proposal.access_url = '/my/proposal/%s' % (proposal.id)

    def preview_sale_proposal(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

    def create_contract(self):
        self.ensure_one()
        so_line_vals = [(0, 0, {
            'product_id': line.product_id.id,
            'name': line.name,
            'price_unit': line.price_accepted,
            'product_uom_qty': line.qty_accepted,
            'display_type': line.display_type,
        }) for line in self.proposal_line]
        so_vals = {
            'partner_id': self.user_id.partner_id.id,
            'user_id': self.user_id.id,
            'state': 'sale',
            'order_line': so_line_vals,
        }
        order_id = self.env['sale.order'].create(so_vals)

        return order_id


class SaleProposalLine(models.Model):
    _name = 'sale.proposal.line'
    _description = 'Proposal Lines'

    @api.depends('qty_proposed', 'price_proposed')
    def _compute_subtotal_proposed_price(self):
        pro_total = 0.0
        for pro in self:
            pro_total = (pro.price_proposed * pro.qty_proposed)
            pro.update({
                'subtotal_price_proposed': pro_total,
            })


    @api.depends('qty_accepted', 'price_accepted')
    def _compute_subtotal_accepted_price(self):
        accept_total = 0.0
        for accept in self:
            accept_total = (accept.price_accepted * accept.qty_accepted)
            accept.update({
                'subtotal_price_accepted': accept_total,
            })


    sale_proposal_id = fields.Many2one('sale.proposal', string='Proposal Reference', required=True,
                     ondelete='cascade', index=True, copy=False)
    name = fields.Text(string='Description', required=True)
    product_id = fields.Many2one('product.product', string='Product',
        change_default=True, ondelete='restrict')
    qty_proposed = fields.Float("Qty Proposed", required=True, default=1.0)
    qty_accepted = fields.Float("Qty Accepted")
    price_proposed = fields.Float("Price Proposed")
    price_accepted = fields.Float("Price Accepted")
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                 domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True)
    currency_id = fields.Many2one(related='sale_proposal_id.currency_id',
                depends=['sale_proposal_id.currency_id'], store=True, string='Currency', readonly=True)
    product_no_variant_attribute_value_ids = fields.Many2many('product.template.attribute.value',
                string="Extra Values", ondelete='restrict')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")

    #Total related fields
    subtotal_price_proposed = fields.Float("Subtotal Price Proposed",
                   compute="_compute_subtotal_proposed_price")
    subtotal_price_accepted = fields.Float("Subtotal Price Accepted",
                  compute="_compute_subtotal_accepted_price")

    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return
        # remove the no_variant attributes that don't belong to this template
        for ptav in self.product_no_variant_attribute_value_ids:
            if ptav._origin not in valid_values:
                self.product_no_variant_attribute_value_ids -= ptav
        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['qty_proposed'] = self.qty_proposed or 1.0

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.sale_proposal_id.partner_id.lang).code,
            partner=self.sale_proposal_id.partner_id,
            quantity=vals.get('qty_proposed') or self.qty_proposed,
            pricelist=self.sale_proposal_id.pricelist_id.id,
            uom=self.product_uom.id
        )

        vals.update(name=self.get_product_description_sale(product))
        self.update(vals)
        if self.sale_proposal_id.pricelist_id and self.sale_proposal_id.partner_id:
            vals['price_proposed'] = self._get_display_price(product)
        self.update(vals)

    def get_product_description_sale(self, product):
        return product.get_product_multiline_description_sale()

    def _get_display_price(self, product):
        no_variant_attributes_price_extra = [
            ptav.price_extra for ptav in self.product_no_variant_attribute_value_ids.filtered(
                lambda ptav:
                    ptav.price_extra and
                    ptav not in product.product_template_attribute_value_ids
            )
        ]
        if no_variant_attributes_price_extra:
            product = product.with_context(
                no_variant_attributes_price_extra=tuple(no_variant_attributes_price_extra)
            )

        if self.sale_proposal_id.pricelist_id.discount_policy == 'with_discount':
            return product.with_context(pricelist=self.sale_proposal_id.pricelist_id.id).price
        product_context = dict(self.env.context, partner_id=self.sale_proposal_id.partner_id.id, date=fields.Date.today(), uom=self.product_uom.id)

        final_price, rule_id = self.sale_proposal_id.pricelist_id.with_context(product_context).get_product_price_rule(self.product_id, self.product_uom_qty or 1.0, self.sale_proposal_id.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.product_uom_qty, self.product_uom, self.sale_proposal_id.pricelist_id.id)
        if currency != self.sale_proposal_id.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, self.sale_proposal_id.pricelist_id.currency_id,
                self.env.company, fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)

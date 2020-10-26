# -*- coding: utf-8 -*-
import werkzeug
import base64
import json
import binascii

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.osv import expression


class Proposal(CustomerPortal):

    @http.route(['/my/proposal/<int:proposal_id>'], type='http', auth="public", website=True)
    def my_proposal(self, proposal_id, report_type=None, access_token=None, message=False, download=False, **post):
        ProposalForm = request.env['sale.proposal'].sudo()
        proposal = ProposalForm.sudo().browse(proposal_id)

        # if report_type in ('html', 'pdf', 'text'):
        #     return self._show_report(model=proposal, report_type=report_type, report_ref='proposal_v13.report_proposal', download=download)

        values = {
            'proposal' : proposal,
        }
        return request.render('proposal_v13.sale_proposal_template', values)


    @http.route('/my/proposal/<int:proposal_id>/accept', type='http', methods=['POST'], auth="public", website=True, csrf=False)
    def portal_proposal_accept(self, **kw):
        proposal_list = []
        if kw:
            proposal = request.env['sale.proposal'].sudo().browse(kw['proposal_id'])
            qty_accepted_list = request.httprequest.form.getlist('qty_accepted')
            price_accepted_list = request.httprequest.form.getlist('price_accepted')
            line_id_list = request.httprequest.form.getlist('line_id')

            res = dict(zip(zip(price_accepted_list,qty_accepted_list),line_id_list))
            for key, value in res.items():
                if key and value:
                    line = request.env['sale.proposal.line'].sudo().browse(int(value))
                    if float(key[1]) > line.qty_proposed or float(key[0]) > line.price_proposed:
                        return request.render("proposal_v13.redirect_fail_page")
                    proposal_list.append([1,int(value),{
                        'sale_proposal_id': proposal.id,
                        'qty_accepted': key[1] or 0.0,
                        'price_accepted': key[0] or 0.0,
                        }])

            proposal.write(
                {'proposal_line': proposal_list,
                'is_proposal_accepted': True,
                })

            redirect = '/page/thank_you/' + str(proposal.id)
            return http.redirect_with_hash(redirect)


    @http.route('/page/thank_you/<int:proposal_id>', type='http', auth="public",
                methods=['POST', 'GET'], website=True)
    def thank_you(self, proposal_id, **kw):
        ProposalForm = request.env['sale.proposal'].sudo()
        proposal = ProposalForm.sudo().browse(proposal_id)

        return request.render('proposal_v13.thank_page_view', {
            'proposal': proposal,
        })


    @http.route(['/my/proposal/<int:proposal_id>/decline'], type='http', auth="public", methods=['POST'], website=True)
    def decline(self, proposal_id, access_token=None, **post):
        try:
            proposal_sudo = self._document_check_access('sale.proposal', proposal_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/')

        message = post.get('decline_message')

        query_string = False
        if message:
            proposal_sudo.state = 'cancel'
            _message_post_helper('sale.proposal', proposal_id, message, **{'token': access_token} if access_token else {})
        else:
            query_string = "&message=cant_reject"

        return request.redirect(proposal_sudo.get_portal_url(query_string=query_string))

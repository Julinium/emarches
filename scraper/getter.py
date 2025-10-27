import re, requests, traceback
from bs4 import BeautifulSoup, Comment

from scraper import helper
from scraper import constants as C

# import os
# import django
# from django.conf import settings

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scraper.settings")
# django.setup()


from base.models import Tender

# NA_PLH = C.NA_PLH
NA_PLH = None

def getJson(link_item, skipExisting=False):

    """
    # Synapsis:
        From a link, gets a structured object (JSON) representing data of the Consultation and all its related objects
    # Params:
        link_item: a line of the generated links file, containing pudlication date, portal id and organization acronym.
    # Return:
        JSON object representing data.
    """

    

    if link_item == None or len(link_item) < 3:
        helper.printMessage('ERROR', 'g.getJson', 'Got an invalid link item.')
        return None
    helper.printMessage('DEBUG', 'g.getJson', f'Getting objects for item id = {link_item[0]}')
    if skipExisting:
        e = Tender.objects.filter(chrono=link_item[0])
        if e.first():
            helper.printMessage('DEBUG', 'g.getJson', f'Tender {link_item[0]} exists and Skipping ON.', 0, 1)
            return None
    

    cons_uri = f"{link_item[0]}{C.LINK_STITCH}{link_item[1]}"
    cons_link = f'{C.LINK_PREFIX}{cons_uri}'
    dce_link = f'{C.SITE_INDEX}?page=entreprise.EntrepriseDownloadCompleteDce&reference={link_item[0]}&orgAcronym={link_item[1]}'

    rua = helper.getUa()
    rua_label = "Random"
    try:
        start_delimiter = "Mozilla/5.0 ("
        end_delimiter = "; "
        start_index = rua.index(start_delimiter) + len(start_delimiter)
        end_index = rua.index(end_delimiter, start_index)
        rua_label = rua[start_index:end_index]
    except ValueError as ve:
        helper.printMessage('ERROR', 'g.getJson', f'Error trimming UA: {str(ve)}')
    
    helper.printMessage('DEBUG', 'g.getJson', f'Using UA: {rua_label}.')
    headino = {"User-Agent": rua }
    sessiono = requests.Session()

    cons_bytes = None
    try:
        dce_head = sessiono.head(dce_link, headers=headino, timeout=C.REQ_TIMEOUT, allow_redirects=True)
        if dce_head.status_code == 200 :
            if 'Content-Length' in dce_head.headers:
                cons_bytes = int(dce_head.headers['Content-Length'])
            # return None
        else:
            helper.printMessage('WARN', 'g.getJson', f'Request to DCE Header page returned a {dce_head.status_code} status code.')
            if dce_head.status_code == 429:
                helper.printMessage('WARN', 'g.getJson', f'Too many Requests, said the server: {dce_head.status_code} !')
                helper.sleepRandom(300, 600)
    except Exception as x:
        helper.printMessage('WARN', 'g.getJson', f'Exception raised while getting file size at {str(dce_link)}: {str(x)}')
        # return None

    try: request_cons = sessiono.get(cons_link, headers=headino, timeout=C.REQ_TIMEOUT)  # driver.get(lots_link)
    except Exception as x:
        helper.printMessage('ERROR', 'g.getJson', f'Exception raised while getting Cons at {str(cons_link)}: {str(x)}')
        return None
    helper.printMessage('DEBUG', 'g.getJson', f'Getting Cons page : {request_cons}')
    if request_cons.status_code != 200 :
        helper.printMessage('ERROR', 'g.getJson', f'Request to Cons page returned a {request_cons.status_code} status code.')
        if request_cons.status_code == 429:
            helper.printMessage('ERROR', 'g.getJson', f'Too many Requests, said the server: {request_cons.status_code} !')
            helper.sleepRandom(300, 600)
        return None

    bowl = BeautifulSoup(request_cons.text, 'html.parser')


    soup = bowl.find(class_='recap-bloc')

    cons_idddd = link_item[0].strip()
    cons_pub_d = link_item[2].strip()

    #############
    try:
        deadl_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_dateHeureLimiteRemisePlis')
        cons_deadl = deadl_span.get_text().strip() if deadl_span else NA_PLH

        picto_img  = soup.find('img', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_pictCertificat')
        picto_src  = picto_img['src'].strip() if picto_img else NA_PLH
        cons_repec = picto_src.strip().replace('themes/images/', '').replace('.gif', '')

        cance_span = soup.find('img', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_pictConsultationAnnulee')
        cons_cance = "Oui" if cance_span else NA_PLH

        category = None
        categ_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_categoriePrincipale')
        cons_categ = categ_span.get_text().strip() if categ_span else NA_PLH
        if cons_categ != NA_PLH:
            category = {"label": cons_categ}

        refce_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_reference')
        cons_refce = refce_span.get_text().strip() if refce_span else NA_PLH

        objet_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_objet')
        cons_objet = objet_span.get_text().strip() if objet_span else NA_PLH

        helper.printMessage('DEBUG', 'g.getJson', f'Found item {cons_idddd}')

        client = None
        achet_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_entiteAchat')
        cons_achet = achet_span.get_text().strip() if achet_span else NA_PLH
        if cons_achet and len(cons_achet) > 3:
            if cons_achet != NA_PLH:
                client = {"name": cons_achet}

        kind = None
        kind_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_annonce')
        cons_kind = kind_span.get_text().strip() if kind_span else NA_PLH
        if cons_kind and len(cons_kind) > 3:
            if cons_kind != NA_PLH:
                kind = {"name": cons_kind}

        procedure = None
        proce_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_typeProcedure')
        cons_proce = proce_span.get_text().strip() if proce_span else NA_PLH
        if cons_proce and len(cons_proce) > 3:
            if cons_proce != NA_PLH:
                procedure = {"name": cons_proce}

        mode = None
        passa_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_modePassation')
        cons_passa = passa_span.get_text().replace('|', '').strip() if passa_span else NA_PLH
        if cons_passa and len(cons_passa) > 3:
            if cons_passa != NA_PLH:
                mode = {"name": cons_passa}

        lexec_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_lieuxExecutions')
        cons_lexec = lexec_span.get_text().strip() if lexec_span else NA_PLH

        domai_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_domainesActivite')
        domains = []
        domai_lis  = domai_span.find_all('li')
        for domai_li in domai_lis:
            domain = domai_li.get_text().strip() if domai_li else NA_PLH
            if domain and len(domain) > 3:
                if domain != NA_PLH : domains.append({"name": domain})

        add_r_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_adresseRetraitDossiers')
        cons_add_r = add_r_span.get_text().strip() if add_r_span else NA_PLH

        add_d_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_adresseDepotOffres')
        cons_add_d = add_d_span.get_text().strip() if add_d_span else NA_PLH

        add_o_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_lieuOuverturePlis')
        cons_add_o = add_o_span.get_text().strip() if add_o_span else NA_PLH

        plans_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_prixAcquisitionPlan')
        cons_plans = plans_span.get_text().strip() if plans_span else NA_PLH

        adm_n_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_contactAdministratif')
        cons_adm_n = adm_n_span.get_text().strip() if adm_n_span else NA_PLH

        adm_m_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_email')
        cons_adm_m = adm_m_span.get_text().strip() if adm_m_span else NA_PLH

        adm_t_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_telephone')
        cons_adm_t = adm_t_span.get_text().strip() if adm_t_span else NA_PLH

        adm_f_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_telecopieur')
        cons_adm_f = adm_f_span.get_text().strip() if adm_f_span else NA_PLH

        reser_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_idRefRadio_RepeaterReferentielRadio_ctl0_labelReferentielRadio')
        cons_reser = reser_span.get_text().strip() if reser_span else NA_PLH

        qualifs = []
        quali_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_qualification')
        quali_lis  = quali_span.find_all('li')
        for quali_li in quali_lis:
            qualif = quali_li.get_text().strip() if quali_li else NA_PLH
            if qualif != NA_PLH : 
                qualifs.append({"name": qualif})

        agrements = []
        agrem_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_agrements')
        agrem_lis  = agrem_span.find_all('li')
        for agrem_li in agrem_lis:
            agrement = agrem_li.get_text().strip() if agrem_li else NA_PLH
            if agrement != NA_PLH : agrements.append({"name": agrement})

        samples = []
        ech_d_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_dateEchantillons')
        cons_ech_d = ech_d_span.get_text().strip() if ech_d_span else NA_PLH
        ech_a_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_adresseEchantillons')
        cons_ech_a = ech_a_span.get_text().strip() if ech_a_span else NA_PLH
        if cons_ech_d and len(cons_ech_d) > 3 :
            if cons_ech_d != NA_PLH or cons_ech_a != NA_PLH:
                samples.append({"when": cons_ech_d, "description": cons_ech_a})

        meetings = []
        reu_d_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_dateReunion')
        cons_reu_d = reu_d_span.get_text().strip() if reu_d_span else NA_PLH
        reu_a_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_adresseReunion')
        cons_reu_a = reu_a_span.get_text().strip() if reu_a_span else NA_PLH
        if (cons_reu_d and len(cons_reu_d) > 3) or (cons_reu_a and len(cons_reu_a) > 3) :
            if cons_reu_d != NA_PLH or cons_reu_a != NA_PLH:
                meetings.append({"when": cons_reu_d, "description": cons_reu_a})

        visits = []
        vis_d_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_repeaterVisitesLieux_ctl1_dateVisites')
        cons_vis_d = vis_d_span.get_text().strip() if vis_d_span else NA_PLH
        vis_a_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_repeaterVisitesLieux_ctl1_adresseVisites')
        cons_vis_a = vis_a_span.get_text().strip() if vis_a_span else NA_PLH
        if cons_vis_d != NA_PLH or cons_vis_a != NA_PLH:
            visits.append({"when": cons_vis_d, "description": cons_vis_a})

        varia_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_varianteValeur')
        cons_varia = varia_span.get_text().strip() if varia_span else NA_PLH

        estim_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_idReferentielZoneText_RepeaterReferentielZoneText_ctl0_labelReferentielZoneText')
        cons_estim = estim_span.get_text().strip() if estim_span else NA_PLH

        cauti_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_cautionProvisoire')
        cons_cauti = cauti_span.get_text().strip() if cauti_span else NA_PLH

        sized_anch = bowl.find('a', id='ctl0_CONTENU_PAGE_linkDownloadDce')
        cons_sized = sized_anch.get_text().strip() if sized_anch else NA_PLH
        cons_sized = sized_anch.get_text().strip('Dossier de consultation -').strip() if sized_anch else NA_PLH

        nbrlo_span = soup.find('span', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_nbrLots')
        cons_nbrlo = nbrlo_span.get_text().replace('Lots', '').strip() if nbrlo_span else "1"
        if cons_nbrlo == "": cons_nbrlo = "1"

        lots_span = soup.find('a', id='ctl0_CONTENU_PAGE_idEntrepriseConsultationSummary_linkDetailLots')
        lots_href = ""
        if lots_span and lots_span.has_attr('href'): 
            lots_href = lots_span['href']

        #######################

        if len(lots_href) > 2:
            cons_lots = getLots(lots_href)
        else:
            cons_lots = [
                {
                    "number": 1,
                    "title": cons_objet,
                    "category": category,
                    "description": "",
                    "estimate": cons_estim,
                    "bond": cons_cauti,
                    "reserved": cons_reser,
                    "qualifs": qualifs,
                    "agrements": agrements,
                    "samples": samples,
                    "meetings": meetings,
                    "visits": visits,
                    "variant": cons_varia,
                    }
                ]

        cons_dict = {
            "published": cons_pub_d,
            "deadline": cons_deadl,
            "cancelled": cons_cance,
            "reference": cons_refce,
            "category": category,
            "title": cons_objet,
            "lots_count": cons_nbrlo,
            "location": cons_lexec,
            "client": client,
            "kind": kind,
            "procedure": procedure,
            "mode": mode,
            "ebid_esign": cons_repec,
            "lots": cons_lots,
            "plans_price": cons_plans,
            "domains": domains,
            "address_withdrawal": cons_add_r,
            "address_bidding": cons_add_d,
            "address_opening": cons_add_o,
            "contact_name": cons_adm_n,
            "contact_email": cons_adm_m,
            "contact_phone": cons_adm_t,
            "contact_fax": cons_adm_f,
            "chrono": cons_idddd,
            "link": cons_uri,
            "size_read": cons_sized,
            "size_bytes": cons_bytes,
            }

        helper.printMessage('INFO', 'g.getJson', f'Finished getting objects for item {link_item[0]}')
        return cons_dict

    except:
        helper.printMessage('ERROR', 'g.getJson', f'Exception getting objects for item {link_item[0]}')
        traceback.print_exc()
        return None


def getLots(lots_href):
    helper.printMessage('INFO', 'g.getLots', 'Item is multi-lot. Reading lots ... ')
    lots_link = C.SITE_INDEX + lots_href.replace("javascript:popUp('index.php", "").replace("%27,%27yes%27)", "")

    rua = helper.getUa()
    rua_label = "Random"
    try:
        start_delimiter = "Mozilla/5.0 ("
        end_delimiter = "; "
        start_index = rua.index(start_delimiter) + len(start_delimiter)
        end_index = rua.index(end_delimiter, start_index)
        rua_label = rua[start_index:end_index]
    except ValueError as ve:
        helper.printMessage('WARN', 'g.getLots', f'Error trimming UA: {str(ve)}')
    
    helper.printMessage('DEBUG', 'g.getLots', f'Using UA: {rua_label}.')
    headino = {"User-Agent": rua }

    sessiono = requests.Session()

    try: request_lots = sessiono.get(lots_link, headers=headino, timeout=C.REQ_TIMEOUT)  # driver.get(lots_link)
    except Exception as x:
        helper.printMessage('ERROR', 'g.getLots', f'Exception raised while getting lots at {str(lots_link)}: {str(x)}')
        return None
    helper.printMessage('DEBUG', 'g.getLots', f'Getting Lots page : {request_lots}')
    if request_lots.status_code != 200 :
        helper.printMessage('ERROR', 'g.getLots', f'Request to Lots page returned a {request_lots.status_code} status code.')
        if request_lots.status_code == 429:
            helper.printMessage('ERROR', 'g.getLots', f'Too many Requests, said the server: {request_lots.status_code} !')
            helper.sleepRandom(300, 600)
        return None

    bowl = BeautifulSoup(request_lots.text, 'html.parser')

    soup = bowl.find(class_='content')

    lots = []

    def iscomment(elem):
        return isinstance(elem, Comment)

    separator = soup.find('div', class_='separator')
    comments = soup.find_all(string=iscomment)
    i = 0
    for comment in comments:
        if "Debut Lot 1" in comment :
            current_lot = {}

            # Number
            number_elem = comment.find_next_sibling("div", class_="intitule-bloc intitule-150")
            number_span = number_elem.find(class_='blue bold')
            number = number_span.get_text().strip('Lot').strip(':').strip() if number_span else NA_PLH

            # Title
            title_elem = number_elem.find_next_sibling("div", class_="content-bloc bloc-600")
            title = title_elem.get_text().strip() if title_elem else NA_PLH

            # Category
            category = None
            category_elem = title_elem.find_next_sibling("div", class_="content-bloc bloc-600")
            categ = category_elem.get_text().strip() if category_elem else NA_PLH
            if categ and len(categ) > 3:
                if categ != NA_PLH:
                    category = {"label": categ}
            

            # Extract Description
            description_elem = category_elem.find_next_sibling("div", class_="content-bloc bloc-600")
            description = description_elem.get_text().strip() if description_elem else NA_PLH

            # Estimation
            div_id  = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_idReferentielZoneTextLot_RepeaterReferentielZoneText_ctl0_panelReferentielZoneText'
            span_id = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_idReferentielZoneTextLot_RepeaterReferentielZoneText_ctl0_labelReferentielZoneText'
            estimation_div  = description_elem.find_next_sibling("div", id=div_id)
            estimation_span = estimation_div.find('span', id=span_id)
            estimation = estimation_span.get_text().strip() if estimation_span else NA_PLH

            # Caution Provisoire
            div_id  = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_panelCautionProvisoire'
            span_id = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_cautionProvisoire'
            caution_div  = estimation_div.find_next_sibling("div", id=div_id)
            caution_span = caution_div.find('span', id=span_id)
            caution = caution_span.get_text().strip() if caution_span else NA_PLH


            # Qualifications
            qualifs = []
            div_id  = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_panelQualification'
            span_id = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_qualification'
            qualifs_div  = caution_div.find_next_sibling("div", id=div_id)
            qualifs_span = qualifs_div.find('span', id=span_id)
            qualifs_lis = qualifs_span.find_all('li')
            for qualifs_li in qualifs_lis :
                qualif = qualifs_li.get_text().strip() if qualifs_li else NA_PLH
                if qualif and len(qualif) > 3:
                    if qualif != NA_PLH : qualifs.append({"name": qualif})

            # Agrements
            div_id  = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_panelAgrements'
            span_id = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_agrements'
            agrements_div  = qualifs_div.find_next_sibling("div", id=div_id)
            agrements_span = agrements_div.find('span', id=span_id)
            agrements_lis = agrements_span.find_all('li')
            agrements = []
            for agrements_li in agrements_lis :
                agrement = agrements_li.get_text().strip() if agrements_li else NA_PLH
                if agrement and len(agrement) > 3:
                    if agrement != NA_PLH :
                        agrements.append({"name": agrement,})

            # Samples
            div_id  = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_panelEchantillons'
            samples_div  = agrements_div.find_next_sibling("div", id=div_id)
            samples_lis = samples_div.find_all('li')
            samples = []
            for samples_li in samples_lis :
                span_d_id = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_repeaterVisitesLieux_ctl1_Echantillons'
                span_l_id = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_repeaterVisitesLieux_ctl1_Echantillons'
                sample_spans = samples_li.find_all('span')
                if sample_spans and len(sample_spans) > 1 :
                    sample_date = sample_spans[0].get_text().strip() if sample_spans[0] else NA_PLH
                    sample_lieu = sample_spans[1].get_text().strip() if sample_spans[1] else NA_PLH

                    if (sample_date and len(sample_date) > 3) or (sample_lieu and len(sample_lieu) > 3):
                        if sample_date != NA_PLH or sample_lieu != NA_PLH:
                            sample = {
                                "when": re.sub(r'\s+', ' ', sample_date).strip(),
                                "description": re.sub(r'\s+', ' ', sample_lieu).strip(),
                                }
                            samples.append(sample)

            div_id  = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_panelReunion'
            span_id_d = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_dateReunion'
            span_id_a = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_adresseReunion'
            meeting_div  = samples_div.find_next_sibling("div", id=div_id)
            meeting_span_d = meeting_div.find('span', id=span_id)
            meeting_span_a = meeting_div.find('span', id=span_id)
            meeting_d = meeting_span_d.get_text().strip() if meeting_span_d else NA_PLH
            meeting_a = meeting_span_a.get_text().strip() if meeting_span_a else NA_PLH
            meetings = []
            if (meeting_d and len(meeting_d) > 3) or (meeting_a and len(meeting_a) > 3) : 
                if meeting_d != NA_PLH or meeting_a != NA_PLH:
                    meetings.append({"when": meeting_d, "description": meeting_a})
            

            div_id  = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_panelVisitesLieux'
            visits_div  = meeting_div.find_next_sibling("div", id=div_id)
            visits_lis = visits_div.find_all('li')
            visits = []
            for visits_li in visits_lis :
                span_d_id = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_repeaterVisitesLieux_ctl1_dateVisites'
                span_l_id = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_repeaterVisitesLieux_ctl1_dateVisites'
                visit_spans = visits_li.find_all('span')
                if visit_spans and len(visit_spans) > 1 :
                    visit_date = visit_spans[0].get_text().strip() if visit_spans[0] else NA_PLH
                    visit_lieu = visit_spans[1].get_text().strip() if visit_spans[1] else NA_PLH
                    if (visit_date and len(visit_date) > 3) or (visit_lieu and len(visit_lieu) > 3):
                        if visit_date != NA_PLH or visit_lieu != NA_PLH:
                            visit = {
                                "when": re.sub(r'\s+', ' ', visit_date).strip(),
                                "description": re.sub(r'\s+', ' ', visit_lieu).strip(),
                                }
                            visits.append(visit)


            # Variante
            div_id  = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_panelVariante'
            span_id = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_varianteValeur'
            variante_div  = visits_div.find_next_sibling("div", id=div_id)
            variante_span = variante_div.find("div", class_="content-bloc bloc-600")
            variante = variante_span.get_text().strip() if variante_span else NA_PLH


            # ReservePME
            div_id  = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_idRefRadio_RepeaterReferentielRadio_ctl0_panelReferentielRadio'
            span_id = f'ctl0_CONTENU_PAGE_repeaterLots_ctl{i}_idRefRadio_RepeaterReferentielRadio_ctl0_labelReferentielRadio'
            pme_div  = variante_div.find_next_sibling("div", id=div_id)
            pme_span = pme_div.find('span', id=span_id)
            pme = pme_span.get_text().strip() if pme_span else NA_PLH


            # Store extracted data for current lot

            current_lot = {
                "number": number,
                "title": title,
                "category": category,
                "description": description,
                "estimate": estimation,
                "bond": caution,
                "qualifs": qualifs,
                "agrements": agrements,
                "samples": samples,
                "meetings": meetings,
                "visits": visits,
                "variant": variante,
                "reserved": pme,
                }

            lots.append(current_lot)
            i += 1
    return lots

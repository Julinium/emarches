import re, requests, traceback
from bs4 import BeautifulSoup, Comment

from scraper import helper
from scraper import constants as C
from base.models import Tender

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
    helper.printMessage('DEBUG', 'g.getJson', f'Getting objects for item id = 
    {link_item[0]}')
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
        helper.printMessage('WARN', 'g.getJson', f'Exception raised while getting file size at {str(dce_link.replace(C.SITE_INDEX, '[...]'))}: {str(x)}')
        # return None

    try: 


        #####################
        # qs_chro = "page=entreprise.ExtraitPV&refConsultation"
        # qs_acro = "orgAcronyme"
        # digest_link = f"{C.SITE_INDEX}?{qs_chro}={link_item[0]}&{ qs_acro }={link_item[1]}"
        # request_digest = sessiono.get(digest_link, headers=headino, timeout=C.REQ_TIMEOUT)
        # pot = BeautifulSoup(request_digest.text, 'html.parser')
        # bowl = pot.find(id='ctl0_CONTENU_PAGE_mainPart')

        # request_digest = sessiono.get(digest_link, headers=headino, timeout=C.REQ_TIMEOUT)

        # if bowl: 
        #     print("YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY\n")
        #     print(bowl)
        #     print("\nYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY\n")
        # else:
        #     print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

        #####################



        request_cons = sessiono.get(cons_link, headers=headino, timeout=C.REQ_TIMEOUT)  # driver.get(lots_link)
    except Exception as x:
        helper.printMessage('ERROR', 'g.getJson', f'Exception raised while getting Tender at {str(cons_link.replace(C.SITE_INDEX, '[...]'))}: {str(x)}')
        return None
    helper.printMessage('DEBUG', 'g.getJson', f'Getting Tender page : {request_cons}')
    if request_cons.status_code != 200 :
        helper.printMessage('ERROR', 'g.getJson', f'Request to Tender page returned a {request_cons.status_code} status code.')
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
        #####################################
        # has_results = False
        # # has_results = ...
        # if has_results:
        #     results = getResults(cons_idddd, link_item[1])
        # else:
        #     results = {}
        #####################################

        cons_dict = {
            "published"         : cons_pub_d,
            "deadline"          : cons_deadl,
            "cancelled"         : cons_cance,
            "reference"         : cons_refce,
            "category"          : category,
            "title"             : cons_objet,
            "lots_count"        : cons_nbrlo,
            "location"          : cons_lexec,
            "client"            : client,
            "kind"              : kind,
            "procedure"         : procedure,
            "mode"              : mode,
            "ebid_esign"        : cons_repec,
            "lots"              : cons_lots,
            "plans_price"       : cons_plans,
            "domains"           : domains,
            "address_withdrawal": cons_add_r,
            "address_bidding"   : cons_add_d,
            "address_opening"   : cons_add_o,
            "contact_name"      : cons_adm_n,
            "contact_email"     : cons_adm_m,
            "contact_phone"     : cons_adm_t,
            "contact_fax"       : cons_adm_f,
            "chrono"            : cons_idddd,
            "link"              : cons_uri,
            "size_read"         : cons_sized,
            "size_bytes"        : cons_bytes,
            # "results"           : results,
            }

        helper.printMessage('DEBUG', 'g.getJson', f'Finished getting objects for item {link_item[0]}')
        return cons_dict

    except:
        helper.printMessage('ERROR', 'g.getJson', f'Exception getting objects for item {link_item[0]}')
        traceback.print_exc()
        return None


def getLots(lots_href):
    helper.printMessage('DEBUG', 'g.getLots', 'Item is multi-lot. Reading lots ... ')
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


			# <div class="intitule-bloc intitule-150"> <span class="blue bold"><span>Lot</span> 1 :</span></div><div class="content-bloc bloc-600">TRAVAUX DE CONSTRUCTION DE 02 TERRAINS DE PROXIMITE TYPE E A LA COMMUNE AGHOUATIM (CENTRE ET BELAABASS) </div><div class="breaker"></div>
			# <div class="intitule-bloc intitule-150"> <span>Catégorie</span> :</div> <div class="content-bloc bloc-600">Travaux</div><div class="breaker"></div>
			# <div class="intitule-bloc intitule-150"> <span>Description</span> :</div><div class="content-bloc bloc-600"></div><div class="breaker"></div>

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
            category_text = category_elem.get_text().strip() if category_elem else NA_PLH
            # if category_text and len(category_text) > 3:
            if category_text != NA_PLH:
                category = {"label": category_text}

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


def getMinutes(chro='', acro=''):
    digest = {}
    if chro == '' or acro == '' : return digest
    qs_chro = "page=entreprise.ExtraitPV&refConsultation"
    qs_acro = "orgAcronyme"
    digest_link = f"{C.SITE_INDEX}?{qs_chro}={chro}&{ qs_acro }={acro}"

    helper.printMessage('DEBUG', 'g.getMinutes', f'Digest link: {digest_link.replace(C.SITE_INDEX, '[...]')}.')
    # print(digest_link)

    rua = helper.getUa()
    rua_label = "Random"
    try:
        start_delimiter = "Mozilla/5.0 ("
        end_delimiter = "; "
        start_index = rua.index(start_delimiter) + len(start_delimiter)
        end_index = rua.index(end_delimiter, start_index)
        rua_label = rua[start_index:end_index]
    except ValueError as ve:
        helper.printMessage('ERROR', 'g.getMinutes', f'Error trimming UA: {ve}')
    
    helper.printMessage('DEBUG', 'g.getMinutes', f'Using UA: {rua_label}.')
    headino = {"User-Agent": rua}
    sessiono = requests.Session()

    helper.printMessage('DEBUG', 'g.getMinutes', 'Getting Digest page ...')
    try:
        request_digest = sessiono.get(digest_link, headers=headino, timeout=C.REQ_TIMEOUT)
    except Exception as x:
        helper.printMessage('ERROR', 'g.getMinutes', f'Exception raised while getting Digest at {str(digest_link.replace(C.SITE_INDEX, '[...]'))}: { x }')
        return None
    if request_digest.status_code != 200 :
        helper.printMessage('ERROR', 'g.getMinutes', f'Request to Digest page returned a {request_digest.status_code} status code.')
        if request_digest.status_code == 429:
            helper.printMessage('ERROR', 'g.getMinutes', f'Too many Requests, said the server: {request_digest.status_code} !')
            helper.sleepRandom(300, 900)
        return None
    else:
        helper.printMessage('DEBUG', 'g.getMinutes', 'Digest page returned status code 200')

    pot = BeautifulSoup(request_digest.text, 'html.parser')
    bowl = pot.find(id='ctl0_CONTENU_PAGE_mainPart')

    if not bowl: return digest


    bidders = []
    try:
        bidders_element = bowl.find(id='entreprisesParticipantesIn')
        table = bidders_element.find("table")
        for tr in table.select("tr:not(thead tr)"):
            td = tr.find("td")
            if td: bidders.append({"name": td.get_text(strip=True)})
    except Exception: pass


    rejected_da = []
    try:
        rejected_da_element = bowl.find(id='entreprisesEcarteesDA')
        table = rejected_da_element.find("table")
        for tr in table.select("tr:not(thead tr)"):
            try:
                bidder_td = tr.find("td")
                if not bidder_td: continue

                bidder_name = bidder_td.get_text(strip=True)

                try:
                    ids_td = tr.find("div").find("td")
                    raw_ids = ids_td.get_text(strip=True)
                    rejected_lots = [ x.strip() for x in raw_ids.split(",")]
                except Exception: rejected_lots = [""]

                rejected_da.append({"name": bidder_name, "lots": rejected_lots})

            except Exception as xc:
                print(f"rejected_da inner Exception: { xc }")
                continue
    except Exception: pass


    accepted_da = []
    try:
        accepted_da_element = bowl.find(id='entreprisesAdmisDA')
        table = accepted_da_element.find("table")
        for tr in table.select("tr:not(thead tr)"):
            try:
                bidder_td = tr.find("td")
                if not bidder_td: continue

                bidder_name = bidder_td.get_text(strip=True)

                try:
                    ids_td = tr.find("div").find("td")
                    raw_ids = ids_td.get_text(strip=True)
                    accepted_lots = [ x.strip() for x in raw_ids.split(",")]
                except Exception: accepted_lots = [""]

                accepted_da.append({"name": bidder_name, "lots": accepted_lots})

            except Exception as xc:
                print(f"accepted_da inner Exception: { xc }")
                continue
    except Exception: pass


    reserved_da = []
    try:
        reserved_da_element = bowl.find(id='entreprisesAdmisSousReserveDA')
        table = reserved_da_element.find("table")
        for tr in table.select("tr:not(thead tr)"):
            try:
                bidder_td = tr.find("td")
                if not bidder_td: continue

                bidder_name = bidder_td.get_text(strip=True)

                try:
                    ids_td = tr.find("div").find("td")
                    raw_ids = ids_td.get_text(strip=True)
                    reserved_lots = [ x.strip() for x in raw_ids.split(",")]
                except Exception: reserved_lots = [""]

                reserved_da.append({"name": bidder_name, "lots": reserved_lots})

            except Exception as xc:
                print(f"reserved_da inner Exception: { xc }")
                continue
    except Exception: pass


    rejected_dt = []
    try:
        rejected_dt_element = bowl.find(id='entreprisesEcarteesDT')
        table = rejected_dt_element.find("table")
        for tr in table.select("tr:not(thead tr)"):
            try:
                bidder_td = tr.find("td")
                if not bidder_td: continue

                bidder_name = bidder_td.get_text(strip=True)
                rejected_lots = [""]
                try:
                    tds = tr.find_all("div")
                    ids_td = tds[1] if len(tds) > 1 else None

                    if ids_td:
                        raw_ids = ids_td.get_text(strip=True)
                        rejected_lots = [ x.strip() for x in raw_ids.split(",")]
                except Exception: pass

                rejected_dt.append({"name": bidder_name, "lots": rejected_lots})

            except Exception as xc:
                print(f"rejected_dt inner Exception: { xc }")
                continue
    except Exception: pass


    financial_offers = []
    try:
        financial_offers_element = bowl.find(id='ctl0_CONTENU_PAGE_entreprisesMontantActesEngagements')
        table = financial_offers_element.find("table")
        for tr in table.select("tr:not(thead tr)"):
            try:
                tds = tr.find_all("td")

                bidder_td = tds[0]
                lot_td = None
                i = 0
                if len(tds) > 3:
                    lot_td = tds[1]
                    i = 1
                amount_before_td = tds[1 + i]
                amount_after_td = tds[2 + i]

                bidder_name = bidder_td.get_text(strip=True)
                lot_number = lot_td.get_text(strip=True) if lot_td else ""
                amount_before = amount_before_td.get_text(strip=True)
                amount_after = amount_after_td.get_text(strip=True)

                financial_offers.append({"name": bidder_name, "lot": lot_number, 
                    "pre_amount": amount_before, "amount": amount_after})

            except Exception as xc:
                print(f"financial_offers inner Exception: { xc }")
                continue
    except Exception as xv: pass


    winner_offers = []
    try:
        winner_offers_element = bowl.find(id='ctl0_CONTENU_PAGE_entreprisesRetenues')
        table = winner_offers_element.find("table")
        for tr in table.select("tr:not(thead tr)"):
            try:
                tds = tr.find_all("td")

                bidder_td = tds[0]
                lot_td = None
                i = 0
                if len(tds) > 2:
                    lot_td = tds[1]
                    i = 1
                amount_winner_td = tds[1 + i]

                bidder_name = bidder_td.get_text(strip=True)
                lot_number = lot_td.get_text(strip=True) if lot_td else ""
                amount_winner = amount_winner_td.get_text(strip=True)

                winner_offers.append({"lot": lot_number, "name": bidder_name, "amount": amount_winner})

            except Exception as xc:
                print(f"winner_offers inner Exception: { xc }")
                continue
    except Exception: pass


    winner_justifs = []
    try:
        winner_justifs_element = bowl.find(id='ctl0_CONTENU_PAGE_justificatifs')
        table = winner_justifs_element.find("table")
        for tr in table.select("tr:not(thead tr)"):
            try:
                tds = tr.find_all("td")

                lot_td = None
                i = 0
                if len(tds) > 1:
                    lot_td = tds[0]
                    i = 1
                winner_justif_td = tds[0 + i]
                
                lot_number = lot_td.get_text(strip=True) if lot_td else ""
                winner_justif = winner_justif_td.get_text(strip=True)

                winner_justifs.append({"lot": lot_number, "justif": winner_justif})

            except Exception as xc:
                print(f"winner_justifs inner Exception: { xc }")
                continue
    except Exception: pass


    failures_text = None
    failed_lots = []
    try:
        failed_lots_element = bowl.find(id='ctl0_CONTENU_PAGE_declarationsInfructueux')
        failures_text = failed_lots_element.get_text(strip=True)
        if failures_text != "Néant":
            failed_list = failures_text.split(":")[1].strip()
            failed_lots = [ x.strip() for x in failed_list.split(",")]
    except Exception: pass


    date_finished = None
    try:
        date_finished_element = bowl.find(id='ctl0_CONTENU_PAGE_dateAchevement').find(class_="margin-left-10")
        date_finished = date_finished_element.get_text(strip=True)
    except Exception: pass


    digest = {
        "chrono"            : chro,
        "acronym"           : acro,
        "bidders"           : bidders,
        "rejected_da"       : rejected_da,
        "accepted_da"       : accepted_da,
        "reserved_da"       : reserved_da,
        "rejected_dt"       : rejected_dt,
        "financial_offers"  : financial_offers,
        "winner_offers"     : winner_offers,
        "winner_justifs"    : winner_justifs,
        "failures_text"     : failures_text,
        "failed_lots"       : failed_lots,
        "date_finished"     : date_finished
    }

    return digest



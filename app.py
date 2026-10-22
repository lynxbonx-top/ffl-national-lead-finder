import time
import pandas as pd
import streamlit as st
from leadfinder import COLUMNS,STATES,search,crawl_site,extract,normalize
st.set_page_config(page_title='FFL National Lead Finder',page_icon='🔎',layout='wide')
st.title('FFL National Lead Finder')
st.caption('Family First Life agents • brokers • agency owners • all 50 US states')
st.info('Research public business information only. Search results are candidates, not verified FFL agents. Affiliation must be supported by a public page; contact details may be agency-wide.')
if 'leads' not in st.session_state:st.session_state.leads=pd.DataFrame(columns=COLUMNS)
if 'candidates' not in st.session_state:st.session_state.candidates=[]
with st.sidebar:
    st.header('Find FFL profiles')
    state=st.selectbox('State',['All states']+[f'{v} ({k})' for k,v in STATES.items()])
    role=st.selectbox('Target',['Agency owners','Brokers','Insurance agents','Agency teams'])
    max_results=st.slider('Search results per query',5,30,10)
    run=st.button('Discover public pages',type='primary',use_container_width=True)
    st.divider()
    st.header('Add known websites')
    url_text=st.text_area('Agency/profile URLs (one per line)',placeholder='https://example-ffl-agency.com/about')
    inspect=st.button('Inspect pasted URLs',use_container_width=True)
    st.divider()
    upload=st.file_uploader('Import existing CSV',type=['csv'])
    if upload and st.button('Merge CSV',use_container_width=True):
        try:
            incoming=pd.read_csv(upload,dtype=str).fillna('')
            st.session_state.leads=normalize(pd.concat([st.session_state.leads,incoming],ignore_index=True))
            st.success('CSV imported')
        except Exception as e:st.error(str(e))
if run:
    region='' if state=='All states' else state.split(' (')[0]
    phrase={'Agency owners':'"agency owner"','Brokers':'"broker"','Insurance agents':'"insurance agent"','Agency teams':'"team"'}[role]
    queries=[f'"Family First Life" {phrase} {region}',f'"FFL" insurance {phrase} {region}']
    results=[]
    for q in queries:
        try:results+=search(q,max_results)
        except Exception as e:st.warning(str(e))
    st.session_state.candidates=list({r['url']:r for r in results if r['url']}.values())
if st.session_state.candidates:
    st.subheader('Search candidates')
    st.caption('These are unverified search results. Inspect public pages to collect evidence and contacts.')
    options={f"{x['title'][:75]} — {x['url']}":x['url'] for x in st.session_state.candidates}
    selected=st.multiselect('Pages to inspect',list(options),default=list(options)[:min(10,len(options))])
    if st.button('Inspect selected candidates'):
        found=[];bar=st.progress(0)
        for i,item in enumerate(selected):
            found+=crawl_site(options[item],max_pages=3)
            bar.progress((i+1)/len(selected))
        st.session_state.leads=normalize(pd.concat([st.session_state.leads,pd.DataFrame(found)],ignore_index=True))
        st.success(f'Added {len(found)} evidence-backed records before deduplication')
if inspect:
    urls=list(dict.fromkeys([x.strip() for x in url_text.splitlines() if x.strip()]))[:30]
    found=[]
    with st.spinner('Inspecting permitted public pages...'):
        for u in urls:found+=crawl_site(u,max_pages=5)
    st.session_state.leads=normalize(pd.concat([st.session_state.leads,pd.DataFrame(found)],ignore_index=True))
    st.success(f'Extracted {len(found)} records before deduplication')
df=st.session_state.leads
c1,c2,c3,c4=st.columns(4)
c1.metric('Unique records',len(df));c2.metric('Emails',int(df.email.ne('').sum()));c3.metric('Phones',int(df.phone.ne('').sum()));c4.metric('Named people',int(df.name.ne('').sum()))
q=st.text_input('Search records')
filter_state=st.selectbox('Filter state',['All']+list(STATES))
status=st.selectbox('Affiliation',['All','Confirmed FFL (page text)','Possible FFL (URL only)','Unverified'])
only_contact=st.checkbox('With email or phone')
shown=df.copy()
if q:shown=shown[shown.astype(str).apply(lambda s:s.str.contains(q,case=False,regex=False)).any(axis=1)]
if filter_state!='All':shown=shown[shown.state==filter_state]
if status!='All':shown=shown[shown.affiliation==status]
if only_contact:shown=shown[shown.email.ne('')|shown.phone.ne('')]
st.dataframe(shown,use_container_width=True,hide_index=True)
st.download_button('Download filtered CSV',shown.to_csv(index=False).encode('utf-8-sig'),'ffl_national_leads.csv','text/csv',disabled=shown.empty)
st.caption('No login bypass, restricted data, personal phone lookup, or automatic messaging. Review affiliations and applicable outreach laws. Export before closing your session.')

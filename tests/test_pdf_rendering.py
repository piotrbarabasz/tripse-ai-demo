"""Controlled rendering semantics; measured pagination is exercised in Chromium."""
from html.parser import HTMLParser

import pytest

from app.document_studio.marketing import Issue
from app.document_studio.models import ImagePosition, OperationalEntry
from app.document_studio.rendering import render_shell
from app.document_studio.rendering.components import photo
from app.document_studio.rendering.sections import table
from app.document_studio.rendering.trip_documents import section, listing, operational_entry


class Contents(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tags=[];self.text=[];self.feed(html)
    def handle_starttag(self, tag, attrs):self.tags.append(tag)
    def handle_data(self, value):self.text.append(value)


def test_long_semantic_text_is_not_prefragmented_or_changed():
    value='\n\n'.join('Żółć <script> & '+str(i) for i in range(160))+'\n'+'A'*9000
    html=section('Pełna treść',value)
    parsed=Contents(html)
    assert parsed.tags.count('section')==1 and parsed.tags.count('p')==1
    assert ''.join(parsed.text)=='Pełna treść'+value
    assert '<script>' not in html


def test_tables_keep_logical_rows_and_cells_without_character_estimates():
    rows=[['09:15 Europe/Warsaw','Długa komórka — '+'Słowo '*2000,'Do ustalenia'],['10:30','Drugi wiersz','Planowane']]
    parsed=Contents(table('Harmonogram',['Godzina','Opis','Status'],rows))
    assert parsed.tags.count('table')==1 and parsed.tags.count('tr')==3 and parsed.tags.count('td')==6
    assert ''.join(parsed.text)=='HarmonogramGodzinaOpisStatus'+''.join(''.join(row) for row in rows)


def test_operational_time_title_and_status_are_not_repeated_for_long_details():
    entry=OperationalEntry(title='SYNTHETIC_TITLE',details='DETAIL_MARKER '+'Opis '*2000,
        start_local='2027-05-01T09:15:00',time_zone='Europe/Warsaw',status='planned')
    html=operational_entry('Przelot testowy',entry)
    assert html.count('SYNTHETIC_TITLE')==1 and html.count('DETAIL_MARKER')==1
    assert html.count('09:15')==1 and html.count('Planowane')==1
    assert Contents(html).tags.count('tr')==2


def test_lists_are_semantic_items_and_preserve_full_values():
    values=['Pierwszy\nwiersz','Drugi <wartość>','Trzeci '+'długi '*1000]
    parsed=Contents(listing('Lista',values))
    assert parsed.tags.count('ul')==1 and parsed.tags.count('li')==3
    assert ''.join(parsed.text)=='Lista'+''.join(values)


@pytest.mark.parametrize('origin,label',[('demo','DEMO'),('synthetic_test','TEST — DANE SYNTETYCZNE')])
def test_origin_labels_preserve_classification_and_do_not_override_validation(origin,label):
    html=render_shell('Dokument',section('Treść','Robocza'),[
        Issue(severity='error',field_path='price',message='Brak ceny')],classification='WEWNĘTRZNE',data_origin=origin)
    assert label in html and 'WEWNĘTRZNE' in html
    assert 'data-valid="false"' in html and 'data-final-valid="false"' in html
    assert "default-src 'none'" in html and 'unsafe-eval' not in html


@pytest.mark.parametrize('x,y,zoom',[(0,100,1),(25,70,1.4),(100,0,3)])
def test_photo_focal_point_and_zoom_remain_explicit(x,y,zoom):
    html=photo('synthetic-asset',ImagePosition(x=x,y=y,zoom=zoom),'Neutralny test')
    assert f'object-position:{float(x)}% {float(y)}%' in html
    assert f'transform:scale({float(zoom)})' in html
    assert 'Neutralny test' in html

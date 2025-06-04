# resources/lib/nfo_generator.py

import json
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom

def parse_nfo(nfo_path):
    try:
        tree = ET.parse(nfo_path)
        root = tree.getroot()

        title = root.findtext('title', default='Unknown Title')
        year = root.findtext('year', default='')
        plot = root.findtext('plot', default='')

        return title, year, plot
    except Exception as e:
        return None, None, None

def generate_nfo(info_json_path, nfo_path = None):
    if not os.path.isfile(info_json_path):
        print(f"Error: File {info_json_path} not found.")
        return

    with open(info_json_path, 'r', encoding='utf-8') as f:
        info_data = json.load(f)

    directory = os.path.dirname(info_json_path)
    base_name = os.path.splitext(os.path.basename(info_json_path))[0]

    if nfo_path is None:
        nfo_path = os.path.join(directory, base_name + '.nfo')

    movie = ET.Element('movie')

    title = ET.SubElement(movie, 'title')
    title.text = info_data.get('title', 'Not available')

    year = ET.SubElement(movie, 'year')
    year.text = str(info_data.get('release_year', ''))

    plot = ET.SubElement(movie, 'plot')
    plot.text = info_data.get('description', 'Not available')

    if 'upload_date' in info_data:
        upload_date = ET.SubElement(movie, 'dateadded')
        upload_date.text = info_data['upload_date']

    if 'thumbnail' in info_data:
        thumbnail = ET.SubElement(movie, 'thumbnail')
        thumbnail.text = info_data['thumbnail']

    if 'url' in info_data:
        url = ET.SubElement(movie, 'url')
        url.text = info_data['url']

    """
    # no pretty format
    tree = ET.ElementTree(movie)
    tree.write(nfo_path, encoding='utf-8', xml_declaration=True)
    """

    xml_str = ET.tostring(movie, 'utf-8')
    reparsed = minidom.parseString(xml_str)
    pretty_xml = reparsed.toprettyxml(indent="\t")
    with open(nfo_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)

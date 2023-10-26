#!/usr/bin/env python
import base64
import re

import fitz

from fitz.utils import getColor, getColorList
from epc.server import EPCServer
from sexpdata import Symbol

server = EPCServer(('localhost', 0))

# def normalize_edges(page, edges):
#     "Transform vimura edges to (normalized) pdf-tools edges."
#     size = doc[page - 1].mediabox_size
#     return [edges[i]/size[0] if i in [0,2] else edges[i]/size[1] for i in range(0,4)]

# def denormalize_edges(page, edges):
#     "Transform (normalized) pdf-tools edges to vimura edges."
#     size = doc[page - 1].mediabox_size
#     return [edges[i]*size[0] if i in [0,2] else edges[i]*size[1] for i in range(0,4)]

# doc = fitz.open("/home/dalanicolai/test.pdf")

@server.register_function
def test(data):
    return data.value()

@server.register_function
def open(doc_file):
    global doc
    # global display_lists
    # global cropbox_positions
    # global text_pages
    doc = fitz.open(doc_file)
    # display_lists = [p.get_displaylist() for p in doc]
    # cropbox_positions = [(lambda c: [c.x, c.y])(p.cropbox_position) for p in doc]
    # text_pages = [dl.get_textpage() for dl in display_lists]

@server.register_function
def init_data(doc_file):
    global display_lists
    global cropbox_positions
    global text_pages
    display_lists = [p.get_displaylist() for p in doc]
    cropbox_positions = [(lambda c: [c.x, c.y])(p.cropbox_position) for p in doc]
    text_pages = [dl.get_textpage() for dl in display_lists]

# TODO implement?
@server.register_function
def close():
    pass

@server.register_function
def number_of_pages():
    return len(doc)

def parse_structured_text(d, t):
    match t:
        case "page":
            return [Symbol("page"), 0, 0, d['width'], d['height'],
                    *parse_structured_text(d['blocks'], "blocks")]
        case "blocks":
            return [[Symbol("block"),
                     *i['bbox'],
                     *parse_structured_text(i['lines'], "lines")]
                    for i in d if 'lines' in i]
        case "lines":
            return [[Symbol("line"),
                     *i['bbox'],
                     *parse_structured_text(i['spans'], "spans")]
                    for i in d if 'spans' in i]
        case "spans":
            return [[Symbol("span"),
                     *i['bbox'],
                     *parse_structured_text(i['chars'], "chars")]
                    for i in d if 'chars' in i]
        case "chars":
            return [[Symbol("char"), *i['bbox'], i['c']] for i in d]

@server.register_function
def structured_text(start_page, end_page, detail):
    start_page = start_page or 0
    end_page = end_page or len(doc)
    detail =  detail or "words"
    return [doc[p].get_text(detail) for p in range(start_page, end_page)]
    # return page
    # if detail == 'djvu':
    #     text = doc[page - 1].get_text('rawdict') if page else [p.get_text('rawdict') for p in doc]
    #     return parse_structured_text(text, "page")
    # else:
    #     return doc[page - 1].get_text(detail) if page else [p.get_text(detail) for p in doc]

@server.register_function
def pagesizes():
    sizes = []
    for p in doc:
        r = p.cropbox
        sizes.append([r[2]-r[0], r[3]-r[1]])
    return sizes

@server.register_function
def renderpage_svg(page, text):
    p = doc[page - 1]
    return p.get_svg_image(fitz.Identity, bool(text))

@server.register_function
def renderpage_base64(page, width, file=None):
    p = doc[page - 1]
    zoom = width/(p.rect[2] - cropbox_positions[page-1][0])
    mat = fitz.Matrix(zoom, zoom)
    pix = p.get_pixmap(matrix=mat)
    if file:
        pix.save(file)
    else:
        # p.clean_contents()
            # mag = display_width / pix.width
            # svg = page.get_svg_image(matrix=fitz.Matrix(mag, mag))
            # return pix.tobytes("ppm")
        return base64.b64encode(pix.tobytes("png")).decode()
        # return pix.tobytes("png")

def renderpage_file(page, width, path, *args):
    p = doc[page - 1]
    zoom = width/p.rect[2]
    mat = fitz.Matrix(zoom, zoom)
    pix = p.get_pixmap(matrix=mat)
    # p.clean_contents()
        # mag = display_width / pix.width
        # svg = page.get_svg_image(matrix=fitz.Matrix(mag, mag))
    pix.save(path)

@server.register_function
def toc():
    return doc.get_toc()

@server.register_function
def metadata():
    return doc.metadata

@server.register_function
# def addannot(page, style, edges):
def addannot(page, edges, style, return_pagedata=False, page_width=False):
    p = doc[page - 1]
    offset = 2 * cropbox_positions[page - 1]
    media_edges = [c+c0 for c,c0 in zip(edges, offset)]
    match style.value():
        case "highlight":
            a = p.add_highlight_annot()
        case "line":
            a = p.add_line_annot(media_edges[0:2], media_edges[2:4])
            # a.set_border(width=1)
            a.set_colors(stroke=(0,0,1), fill=(0,0,1))
            a.set_line_ends(0, fitz.PDF_ANNOT_LE_CLOSED_ARROW)
            a.update()
    if return_pagedata:
        return renderpage_base64(page, page_width) 
    # edges = fitz.Rect(denormalize_edges(page, edges))
    # p.add_highlight_annot(edges)
    # p.add_caret_annot(fitz.Rect(72, 72, 220, 100).tl)

@server.register_function
def editannot():
    pass

@server.register_function
def delannot():
    pass

# TODO create getannots function producing following response
# (((page . 1) (edges 0.15455 0.190049 0.335979 0.238749) (type . highlight) (id . annot-1-1) (flags . 0) (color . "#fefe00") (contents . "") (modified 25003 54259) (label . "Daniel Nicolai") (subject) (opacity . 1.0) (popup-edges) (popup-is-open) (created) (markup-edges (0.15455 0.190049 0.335979 0.238749))) ((page . 1) (edges 0.199907 0.131846 0.32086 0.180546) (type . highlight) (id . annot-1-0) (flags . 0) (color . "#fefe00") (contents . "") (modified 25003 54232) (label . "Daniel Nicolai") (subject) (opacity . 1.0) (popup-edges) (popup-is-open) (created) (markup-edges (0.199907 0.131846 0.32086 0.180546))))
@server.register_function
def getannots():
    return False

# TODO create pagelinks function producing following response
# (((edges 0.141183 0.14789 0.673246 0.16353) (type . goto-dest) (title . "") (page . 125) (top . 0.144794)) ((edges 0.217501 0.165013 0.735103 0.180717) (type . goto-dest) (title . "") (page . 125) (top . 0.402617)) ((edges 0.171309 0.182171 0.686421 0.197805) (type . goto-dest) (title . "") (page . 127) (top . 0.394724)) ((edges 0.141183 0.213566 0.374606 0.229207) (type . goto-dest) (title . "") (page . 129) (top . 0.144794)))
@server.register_function
def pagelinks():
    return False

@server.register_function
def save(filepath):
    doc.save(filepath, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    return True

@server.register_function
def get_annots(page):
    p = doc[page - 1]
    return [list(a.rect) for a in p.annots()]

@server.register_function
def get_contents():
    return p.get_contents()

@server.register_function
def get_drawings():
    return p.get_drawings()

@server.register_function
def getselection(page):
    p = doc[page]
    size = doc[page].mediabox_size
    return [[j[i]/size[0] if i in [0,2] else j[i]/size[1] for i in range(0,4)] for j in p.get_text("blocks")]

search_results = []

@server.register_function
def search(pattern):
    hits = [(t.search(pattern), c) for t,c in zip(text_pages, cropbox_positions)]
    results = []
    for p, h in enumerate(hits, 1):
        if h[0]:
            for q in h[0]:
                mediabox_rect = q.rect
                offset = 2 * h[1]
                r = [c-c0 for c,c0 in zip(mediabox_rect, offset)]
                results.append([p] + r)
    return results

# @server.register_function
# def search(pattern):
#     results = []
#     for n,p in enumerate(doc):
#         for r in p.search_for(pattern):
#             a = p.add_circle_annot(r)
#             a.set_colors(fill=(1,0,0))
#             a.set_opacity(0.5)
#             a.update()
#             results.append([n, list(r)])
#     return [[i] + p for i,p in enumerate(results,1)]

@server.register_function
def list_colors():
    return getColorList()
# @server.register_function
# def search(pattern, start_page, end_page):
#     start_page = start_page or 1
#     end_page = end_page or doc.last_location[1] + 1
#     results = [[list(x) for x in doc[p].search_for(pattern)] for p in range(start_page - 1, end_page - 1)]
#     return [[i,*x] for i,x in enumerate(results, 1) if x]

@server.register_function
def text_blocks():
    return [x for x in [[i] + [b for b in p.get_text('blocks')] # if re.search(pattern, b[4], re.IGNORECASE)]
                        for i,p in enumerate(doc, 1)]
            if x[1:]]

server.print_port()
server.serve_forever()

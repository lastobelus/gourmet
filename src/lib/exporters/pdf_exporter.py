from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import reportlab.platypus as platypus
from reportlab.platypus.flowables import ParagraphAndImage
import reportlab.lib.pagesizes as pagesizes
import reportlab.lib.fonts as fonts
import reportlab.lib.units as units
import reportlab.lib.styles as styles
from gettext import gettext as _
from gourmet import convert
from gourmet import gglobals
from gourmet import ImageExtras
import xml.sax.saxutils
import exporter
import types, re
import tempfile, os.path
import math

DEFAULT_PDF_ARGS = {
    #'pagesize':'letter',
    #'pagemode':'landscape',
    #'left_margin':0.3*inch,
    #'right_margin':0.3*inch,
    #'top_margin':0.3*inch,
    #'bottom_margin':0.3*inch,
    #'base_font_size':8,
    #'mode':('index_cards',(5*inch,3.5*inch))
    }

# Code for MCLine from:
# http://two.pairlist.net/pipermail/reportlab-users/2005-February/003695.html
class MCLine(platypus.Flowable):
    """Line flowable --- draws a line in a flowable"""
    
    def __init__(self,width):
        platypus.Flowable.__init__(self)
        self.width = width
        
    def __repr__(self):
        return "Line(w=%s)" % self.width
    
    def draw(self):
        self.canv.line(0,0,self.width,0)

class ParagraphKeepWithNext (platypus.Paragraph):
    
    keepWithNext = True
    def getKeepWithNext (self): return 1
    

import reportlab.lib.colors as colors
class Star (platypus.Flowable):
    '''A hand flowable.'''
    def __init__(self, size=None, fillcolor=colors.tan, strokecolor=colors.green):
        from reportlab.lib.units import inch
        if size is None: size=12 # 12 point
        self.fillcolor, self.strokecolor = fillcolor, strokecolor
        self.size = size
        # normal size is 4 inches
        
    def getSpaceBefore (self):
        return 6 # 6 points

    def getSpaceAfter (self):
        return 6 # 6 points
        
    def wrap(self, availW, availH):
        if self.size > availW or self.size > availH:
            if availW > availH:
                self.size = availH
            else:
                self.size = availW
        return (self.size,self.size)

    def draw (self):
        size = self.size # * 0.8
        self.draw_star(inner_length=size/4,
                       outer_length=size/2)

    def draw_circle (self, x, y, r):
        # Test...
        canvas = self.canv
        canvas.setLineWidth(0)        
        canvas.setStrokeColor(colors.grey)
        canvas.setFillColor(colors.grey)        
        p = canvas.beginPath()
        p.circle(x,y,r)
        p.close()
        canvas.drawPath(p,fill=1)

    def draw_half_star (self, inner_length=1*inch, outer_length=2*inch, points=5, origin=None):
        canvas = self.canv
        canvas.setLineWidth(0)
        if not origin: canvas.translate(self.size*0.5,self.size*0.5)
        else: canvas.translate(*origin)
        canvas.setFillColor(self.fillcolor)
        canvas.setStrokeColor(self.strokecolor)
        p = canvas.beginPath()
        inner = False # Start on top
        is_origin = True
        #print 'Drawing star with radius',outer_length,'(moving origin ',origin,')'
        for theta in range(0,360,360/(points*2)):
            if 0 < theta < 180: continue
            if inner: r = inner_length
            else: r = outer_length
            x = (math.sin(math.radians(theta)) * r)
            y = (math.cos(math.radians(theta)) * r)
            #print 'POINT:',x,y
            if is_origin:
                p.moveTo(x,y)
                is_origin = False
            else:
                p.lineTo(x,y)
            inner = not inner
        p.close()
        canvas.drawPath(p,fill=1)

    def draw_star (self, inner_length=1*inch, outer_length=2*inch, points=5, origin=None):
        canvas = self.canv
        canvas.setLineWidth(0)
        if not origin: canvas.translate(self.size*0.5,self.size*0.5)
        else: canvas.translate(*origin)
        canvas.setFillColor(self.fillcolor)
        canvas.setStrokeColor(self.strokecolor)
        p = canvas.beginPath()
        inner = False # Start on top
        is_origin = True
        #print 'Drawing star with radius',outer_length,'(moving origin ',origin,')'
        for theta in range(0,360,360/(points*2)):
            if inner: r = inner_length
            else: r = outer_length
            x = (math.sin(math.radians(theta)) * r)
            y = (math.cos(math.radians(theta)) * r)
            #print 'POINT:',x,y
            if is_origin:
                p.moveTo(x,y)
                is_origin = False
            else:
                p.lineTo(x,y)
            inner = not inner
        p.close()
        canvas.drawPath(p,fill=1)


class FiveStars (Star):

    def __init__ (self, height, filled=5, out_of=5,
                  filled_color=colors.black,
                  unfilled_color=colors.lightgrey
                  ):
        self.height = self.size = height
        self.filled = filled
        self.out_of = out_of
        self.filled_color = filled_color; self.unfilled_color = unfilled_color
        self.width = self.height * self.out_of + (self.height * 0.2 * (self.out_of-1)) # 20% padding
        self.ratio = self.height / 12 # 12 point is standard
        

    def wrap (self, *args):
        return self.width,self.height

    def draw (self):
        #self.canv.scale(self.ratio,self.ratio)
        self.draw_stars()

    def draw_stars (self):
        #if self.height
        for n in range(self.out_of):
            if self.filled - n >= 1:
                # Then we draw a gold star
                self.fillcolor,self.strokecolor = self.filled_color,self.filled_color
                r = self.height * 0.5
            else:
                self.fillcolor,self.strokecolor = self.unfilled_color,self.unfilled_color
                r = self.height * 0.75 * 0.5
            origin = (
                # X coordinate
                ((n >= 1 and (self.height * 1.2)) or self.height*0.5),
                # Y coordinate
                ((n < 1 and self.height* 0.5) or 0)
                )
            #print 'origin = ',#origin,'or',
            #print origin[0]/self.height,origin[1]/self.height
            #self.draw_circle(origin[0],origin[1],r)
            self.draw_star(points=5,origin=origin,inner_length=r/2,outer_length=r)
            if self.filled - n == 0.5:
                # If we're a half star...
                self.fillcolor,self.strokecolor = self.filled_color,self.filled_color                
                self.draw_half_star(points=5,
                                    inner_length=self.height*0.25,
                                    outer_length=self.height*0.5,
                                    origin=(0,0)
                                    )
            
class PdfWriter:

    def __init__ (self):
        pass

    def setup_document (self, file, mode=('column',1), size='default', pagesize='letter',
                        pagemode='portrait',left_margin=inch,right_margin=inch,
                        top_margin=inch,
                        bottom_margin=inch,
                        base_font_size=10
                        ):
        if type(mode)!=tuple: raise "What is this mode! %s"%str(mode)
        if type(pagesize) in types.StringTypes:
            self.pagesize = getattr(pagesizes,pagemode)(getattr(pagesizes,pagesize))
        else:
            self.pagesize = pagesize
        self.margins = (left_margin,right_margin,top_margin,bottom_margin)
        if mode[0] == 'column':
            frames = self.setup_column_frames(mode[1])
        elif mode[0] == 'index_cards':
            frames = self.setup_multiple_index_cards(mode[1])
        else:
            raise("WTF - mode = %s"%str(mode))
        pt = platypus.PageTemplate(frames=frames)
        self.doc = platypus.BaseDocTemplate(file,pagesize=self.pagesize,
                                            pageTemplates=[pt],)
        self.doc.frame_width = frames[0].width
        self.doc.frame_height = frames[0].height
        self.styleSheet = styles.getSampleStyleSheet()
        perc_scale = float(base_font_size)/self.styleSheet['Normal'].fontSize
        if perc_scale!=1.0:
            self.scale_stylesheet(perc_scale)
        self.txt = []

    def scale_stylesheet (self, perc):
        for name,sty in self.styleSheet.byName.items():
            for attr in ['firstLineIndent',
                         'fontSize',
                         'leftIndent',
                         'rightIndent',
                         'leading']:
                setattr(sty,attr,int(perc*getattr(sty,attr)))
        
    def setup_column_frames (self, n):
        COLUMN_SEPARATOR = 0.5 * inch
        x = self.pagesize[0]
        y = self.pagesize[1]
        leftM,rightM,topM,bottomM = self.margins
        FRAME_Y = bottomM
        FRAME_HEIGHT = y - topM - bottomM
        FRAME_WIDTH = (x - (COLUMN_SEPARATOR*(n-1)) - leftM - rightM)/n
        frames = []
        for i in range(n):
            left_start = leftM + (FRAME_WIDTH + COLUMN_SEPARATOR)*i
            frames.append(
                platypus.Frame(
                left_start,FRAME_Y,width=FRAME_WIDTH,height=FRAME_HEIGHT
                )
                )
        return frames

    def setup_multiple_index_cards (self,card_size):
        leftM,rightM,topM,bottomM = self.margins
        MINIMUM_SPACING = 0.1*inch
        drawable_x = self.pagesize[0] - leftM - rightM
        drawable_y = self.pagesize[1] - topM - bottomM
        fittable_x = int(drawable_x / (card_size[0]+MINIMUM_SPACING))
        x_spacer = (
            # Extra space = 
            fittable_x * # Number of cards times
            ((drawable_x/fittable_x) # space per card
             - card_size[0] ) # - space occupied by card
            / # Divide extra space by n+1, so we get [   CARD    ], [  CARD  CARD  ], etc.
            (fittable_x+1)
            )
        fittable_y = int(drawable_y / (card_size[1]+MINIMUM_SPACING))
        y_spacer = (
            fittable_y *
            ((drawable_y/fittable_y)
              - (card_size[1]))
             /
            (fittable_y+1)
            )
        if (not fittable_x) or (not fittable_y):
            raise ValueError("Card size %s does not fit on page %s with margins %s"%(
                card_size,self.pagesize,self.margins
                )
                             )
        frames = []
        for x in range(fittable_x):
            x_start = leftM + (x_spacer*(x+1)) + (card_size[0]*x)
            for y in range(fittable_y-1,-1,-1):
                # Count down for the y, since we start from the bottom
                # and move up
                y_start = bottomM + (y_spacer*(y+1)) +  (card_size[1]*y)
                frames.append(
                    platypus.Frame(x_start,y_start,
                                   width=card_size[0],
                                   height=card_size[1],
                                   showBoundary=1)
                    )
        return frames
    
    def make_paragraph (self, txt, style=None, attributes="",keep_with_next=False):
        if attributes:
            txt = '<para %s>%s</para>'%(attributes,xml.sax.saxutils.escape(txt))
        if not style: style = self.styleSheet['Normal']
        try:
            return platypus.Paragraph(unicode(txt).encode('iso-8859-1','replace'),style)
        except UnicodeDecodeError:
            try:
                #print 'WORK AROUND UNICODE ERROR WITH ',txt[:20]
                # This seems to be the standard on windows.
                platypus.Paragraph(txt,style)
            except:
                print 'Trouble with ',txt
                raise
    
    def write_paragraph (self, txt, style=None, keep_with_next=False, attributes=""):
        p = self.make_paragraph(txt,style,attributes,keep_with_next=keep_with_next)
        if keep_with_next:
            # Keep with next isn't working, so we use a conditional
            # page break, on the assumption that no header should have
            # less than 3/4 inch of stuff after it on the page.
            self.txt.append(platypus.CondPageBreak(0.75*inch))
        self.txt.append(p)
        

    def write_header (self, txt):
        """Write a header.

        WARNING: If this is not followed by a call to our write_paragraph(...keep_with_next=False),
        the header won't necessarily be written.
        """
        self.write_paragraph(
            txt,
            style=self.styleSheet['Heading1'],
            keep_with_next = True
            )

    def write_subheader (self, txt):
        """Write a subheader.

        WARNING: If this is not followed by a call to our write_paragraph(...keep_with_next=False),
        the header won't necessarily be written.
        """        
        self.write_paragraph(
            txt,
            style=self.styleSheet['Heading2'],
            keep_with_next=True
            )

    def close (self):
        t = self.txt[:]
        try: self.doc.build(self.txt)
        except:
            print 'Trouble building',t[:20]
            raise
        
class PdfExporter (exporter.exporter_mult, PdfWriter):

    def __init__ (self, rd, r, out,
                  doc=None,
                  styleSheet=None,
                  txt=[],
                  pdf_args=DEFAULT_PDF_ARGS,
                  **kwargs):
        PdfWriter.__init__(self)
        if type(out) in types.StringTypes:
            out = file(out,'wb')
        if not doc:
            self.setup_document(out,**pdf_args)
            self.multidoc = False
        else:
            self.doc = doc; self.styleSheet = styleSheet; self.txt = []
            self.master_txt = txt
            self.multidoc = True
            # Put nice lines to separate multiple recipes out...
            if pdf_args.get('mode',('columns',1))[0]=='columns':
                self.txt.append(MCLine(self.doc.frame_width*0.8))
        exporter.exporter_mult.__init__(
            self,
            rd,r,
            None, # exporter_mult has no business touching a file
            use_ml=True,
            order=['image','attr','ings','text'],
            do_markup=True,
            fractions=convert.FRACTIONS_NORMAL,
            **kwargs
            )
        if not self.multidoc:
            self.close() # Finish the document if this is all-in-one
            out.close()
        else:
            #self.txt.append(platypus.PageBreak()) # Otherwise, a new page
            # Append to the txt list we were handed ourselves in a KeepTogether block
            #self.txt.append(platypus.Spacer(0,inch*0.5))
            #if pdf_args.get('mode',('column',1))[0]=='column':
            #    self.master_txt.append(platypus.KeepTogether(self.txt))
            #else:
            if self.master_txt:
                self.master_txt.append(platypus.FrameBreak())
            self.master_txt.extend(self.txt)
            #self.master_txt.extend(self.txt)

    def handle_italic (self, chunk):
        return '<i>' + chunk + '</i>'
    
    def handle_bold (self, chunk):
        return '<b>' + chunk + '</b>'
    
    def handle_underline (self, chunk):
        return '<u>' + chunk + '</u>'

    def scale_image (self, image, proportion=None):
        # Platypus assumes image size is in points -- this appears to
        # be off by the amount below.
        if not proportion: proportion = inch/100 # we want 100 dots per image
        image.drawHeight = image.drawHeight*proportion        
        image.drawWidth = image.drawWidth*proportion

    def write_image (self, data):
        fn = ImageExtras.write_image_tempfile(data)
        i = platypus.Image(fn)
        self.scale_image(i)
        factor = 1
        MAX_WIDTH = self.doc.frame_width * 0.35
        MAX_HEIGHT = self.doc.frame_height * 0.5
        if i.drawWidth > MAX_WIDTH:
            factor = MAX_WIDTH/i.drawWidth
        if i.drawHeight > MAX_HEIGHT:
            f = MAX_HEIGHT/i.drawHeight
            if f < factor: factor = f
        if factor < 1.0:
            self.scale_image(i,factor)
        self.image = i

    def write_attr_head (self):
        # just move .txt aside through the attrs -- this way we can
        # use our regular methods to keep adding attribute elements 
        self.attributes = []
        
    def write_attr_foot (self):
        # If we have 3 or fewer attributes and no images, we don't
        # need a table
        if len(self.attributes)<=3 and not hasattr(self,'image'):
            self.txt.extend(self.attributes)
            return
        if not self.attributes and hasattr(self,'image'):
            # If we only have an image...
            self.txt.append(self.image)
            return
        elif hasattr(self,'image') and self.image.drawWidth > (self.doc.frame_width / 2.25):
            self.txt.append(self.image)
            self.txt.extend(self.attributes)
            return
        # Otherwise, we're going to make a table...
        if hasattr(self,'image'):
            # If we have an image, we put attributes on the
            # left, image on the right
            table_data = [
                [# 1 row
                # column 1 = attributes
                self.attributes,
                # column 2 = image
                self.image
                ],
                # End of "table"
                ]
        else:
            nattributes = len(self.attributes)
            first_col_size = nattributes/2 + nattributes % 2
            first = self.attributes[:first_col_size]
            second = self.attributes[first_col_size:]
            table_data = []
            for n,left in enumerate(first):
                right = len(second)>n and second[n] or ''
                table_data.append([left,right])
        t = platypus.Table(table_data)
        t.setStyle(
            platypus.TableStyle([
            ('VALIGN',(0,0),(0,-1),'TOP'),
            ('LEFTPADDING',(0,0),(0,-1),0),
            # for debugging
            #('INNERGRID',(0,0),(-1,-1),.25,colors.red),
            #('BOX',(0,0),(-1,-1),.25,colors.red),            
            ]
                                )
            )
        self.txt.append(t)
        #self.txt = [platypus.KeepTogether(self.txt)]

    def make_rating (self, label, val):
        """Make a pretty representation of our rating.
        """
        try:
            assert(type(val)==int)
        except:
            raise TypeError("Rating %s is not an integer"%val)
        i = FiveStars(10, filled=(val/2.0)) # 12 point
        lwidth = len(label+': ')*4 # A very cheap approximation of width
        t = platypus.Table(
            [[label+': ',i]],
            colWidths=[lwidth,inch],
            )
        t.hAlign = 'LEFT'
        t.setStyle(
            platypus.TableStyle([
            ('LEFTPADDING',(0,0),(-1,0),0),
            ('LEFTPADDING',(1,0),(1,0),6),
            ('TOPPADDING',(0,0),(-1,-1),0),
            ('ALIGNMENT',(1,0),(1,0),'LEFT'),
            ('VALIGN',(0,0),(0,0),'TOP'),
            # for debugging
            #('INNERGRID',(0,0),(-1,-1),.25,colors.black),
            #('BOX',(0,0),(-1,-1),.25,colors.black),            
             ]
                                )
            )
        return t
    
    def write_attr (self, label, text):
        attr = gglobals.NAME_TO_ATTR[label]
        if attr=='title':
            self.write_paragraph(text,style=self.styleSheet['Heading1'])
            return
        if attr=='rating':
            from gourmet.importers.importer import string_to_rating
            val = string_to_rating(text)
            if val:
                self.attributes.append(self.make_rating(label,val))
                return
        self.attributes.append(self.make_paragraph("%s: %s"%(label,text)))

    def write_text (self, label, text):
        self.write_subheader(label)
        first_para = True
        for t in text.split('\n'):
            # HARDCODING paragraph style to space
            if first_para:
                first_para = False
            self.write_paragraph(t,attributes="spacebefore='6'")

    def write_inghead (self):
        self.save_txt = self.txt[:]
        self.txt = []
        self.write_subheader(xml.sax.saxutils.escape(_('Ingredients')))

    def write_grouphead (self, name):
        self.write_paragraph(name,self.styleSheet['Heading3'])

    def write_ingfoot (self):
        # Ugly -- we know that heads comprise two elements -- a
        # condbreak and a head...
        ings = self.txt[2:]
        if len(ings) > 4:
            half = (len(ings) / 2)
            first_half = ings[:-half]
            second_half = ings[-half:]
            t = platypus.Table(
                [[first_half,second_half]]
                )
            t.hAlign = 'LEFT'
            t.setStyle(
                platypus.TableStyle([
                ('VALIGN',(0,0),(1,0),'TOP'),
                ]
                                    )
                )
            self.txt = self.txt[:2] + [t]
        self.txt = self.save_txt + [platypus.KeepTogether(self.txt)]

    def write_ing (self, amount=1, unit=None, item=None, key=None, optional=False):
        txt = ""
        for blob in [amount,unit,item,(optional and _('optional') or '')]:
            if not blob: continue
            if txt: txt += " %s"%blob
            else: txt = blob
        hanging = inch*0.25
        self.write_paragraph(
            txt,
            attributes=' firstLineIndent="-%(hanging)s" leftIndent="%(hanging)s"'%locals()
            )
                              

class PdfExporterMultiDoc (exporter.ExporterMultirec, PdfWriter):
    def __init__ (self, rd, recipes, out, progress_func=None, conv=None,
                  pdf_args=DEFAULT_PDF_ARGS,
                  **kwargs):
        PdfWriter.__init__(self)
        if type(out) in types.StringTypes:
            print 'Open binary file ',out
            out = file(out,'wb')
        self.setup_document(out,**pdf_args)
        self.output_file = out
        kwargs['doc'] = self.doc
        kwargs['styleSheet'] = self.styleSheet
        kwargs['txt'] = self.txt
        kwargs['pdf_args'] = pdf_args
        exporter.ExporterMultirec.__init__(
            self,
            rd, recipes, out,
            one_file=True, ext='pdf',
            exporter=PdfExporter,
            conv=conv,
            progress_func=progress_func,
            exporter_kwargs=kwargs,
            )

    def write_footer (self):
        self.close()
        self.output_file.close()
            
if __name__ == '__main__':
    from tempfile import tempdir
    import os.path
    sw = PdfWriter()
    f = file(os.path.join(tempdir,'foo.pdf'),'wb')
    sw.setup_document(f,
                      mode=('index_cards',(5*inch,3.5*inch)),
                      #pagesize=(5*inch,3.5*inch),
                      pagesize='letter',
                      pagemode='landscape',
                      left_margin=0.25*inch,right_margin=0.25*inch,
                      top_margin=0.25*inch,bottom_margin=0.25*inch,
                      base_font_size=8,
                      )
    #sw.write_header('Heading')
    #sw.write_subheader('This is a subheading')
    for n in range(5):
        sw.write_header(
            u"This is a header"
            )
        #sw.write_subheader(
        #    u"This is a subheader"
        #    )
        sw.write_paragraph(
            u"%s: These are some sentences.  Hopefully some of these will be quite long sentences.  Some of this text includes unicode -- 45\u00b0F, for example... \u00bfHow's that?"%n*10
            )
    #sw.write_paragraph('This is a <i>paragraph</i> with <b>some</b> <u>markup</u>.')
    #sw.write_paragraph(u"This is some text with unicode - 45\u00b0, \u00bfHow's that?".encode('iso-8859-1'))
    #sw.write_paragraph(u"This is some text with a unicode object - 45\u00b0, \u00bfHow's that?")
    sw.close()
    f.close()
    
    #star_file = file(os.path.join(tempdir,'star.pdf'),'wb')
    #sw = PdfWriter()
    #sw.setup_document(star_file,mode='two_column')
    #for n in range(6,72,2):
    #    sw.write_paragraph("This is some text with a %s pt star"%n)
    #    sw.txt.append(FiveStars(n,filled=3.5))
    #    
    #sw.close()
    #star_file.close()
    #import gnome
    #gnome.program_init('1.0','Gourmet PDF Exporter Test')
    #gglobals.launch_url('file:/os.path.join(tempdir,/star.pdf')
    #raise "I don')t want to go any further"
    
    import gnome

    if os.name == 'nt':
        base = 'C:\\grm\grm'
    else:
        base = '/home/tom/Projects/grm'

    import gourmet.recipeManager as rm
    #rd = rm.RecipeManager(file=os.path.join(base,'src','tests','reference_setup','recipes.db'))
    rd = rm.RecipeManager()
    #ofi = file(os.path.join(tempdir,'test_rec.pdf'),'w')
    rr = []
    for n,rec in enumerate(rd.fetch_all(rd.rview,deleted=False)):
        if rec.image:
            rr.append(rec)
    #pe = PdfExporterMultiDoc(rd,rd.fetch_all(rd.rview),os.path.join(tempdir,'fooby.pdf'))
    #pe = PdfExporterMultiDoc(rd,rd.fetch_all(rd.rview,deleted=False)[:10],os.path.join(tempdir,'fooby.pdf'))
    pe = PdfExporterMultiDoc(rd,rr,os.path.join(tempdir,'fooby.pdf'))
    pe.run()
    import gourmet.gglobals as gglobals
    try:
        import gnome
        gnome.program_init('1.0','Gourmet PDF Exporter Test')
    except ImportError:
        print 'We must be on windows...'
    print 'Launching',os.path.join(tempdir,'fooby.pdf')
    gglobals.launch_url('file://'+os.path.join(tempdir,'fooby.pdf'))    
    #print 'Launching',os.path.join(tempdir,'star.pdf')
    #gglobals.launch_url('file://'+os.path.join(tempdir,'star.pdf'))


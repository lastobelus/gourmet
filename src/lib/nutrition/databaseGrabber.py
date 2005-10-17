import urllib, zipfile, tempfile, os.path, re, string
from gettext import gettext as _
from parser_data import *
from gourmet.gdebug import *
expander_regexp = None

def compile_expander_regexp ():    
    regexp = "(?<!\w)("
    regexp += string.join(ABBREVS.keys(),"|")
    regexp += ")(?!\w)"
    return re.compile(regexp)

def expand_abbrevs ( line ):
    """Expand standard abbreviations."""
    global expander_regexp
    for k,v in ABBREVS_STRT.items():
        line = line.replace(k,v)
    if not expander_regexp:
        expander_regexp=compile_expander_regexp()
    ematch = expander_regexp.search(line)
    while ematch:
        matchstr=ematch.groups()[0]
        replace=ABBREVS[str(matchstr)]
        line = line[0:ematch.start()] + replace + line[ematch.end():]
        ematch = expander_regexp.search(line)
    return line

class DatabaseGrabber:
    USDA_ZIP_URL = "http://www.nal.usda.gov/fnic/foodcomp/Data/SR17/dnload/sr17abbr.zip"
    ABBREV_FILE_NAME = "ABBREV.txt"
    WEIGHT_FILE_NAME = "WEIGHT.txt"

    def __init__ (self,
                  db,
                  show_progress=None):
        self.show_progress=show_progress
        self.db = db
        
    def get_zip_file (self):
        if hasattr(self,'zipfile'):
            return self.zipfile
        else:
            ofi = urllib.urlopen(self.USDA_ZIP_URL)
            tofi = tempfile.TemporaryFile()
            tofi.write(ofi.read())
            tofi.seek(0)
            self.zipfile = zipfile.ZipFile(tofi,'r')
            return self.zipfile
        
    def get_file_from_url (self, filename):
        zf = self.get_zip_file()
        tofi2 = tempfile.TemporaryFile()
        tofi2.write(zf.read(filename))
        tofi2.seek(0)
        return tofi2

    def get_abbrev (self, filename=None):
        if filename:
            afi = open(filename,'r')
        else:
            afi = self.get_file_from_url(self.ABBREV_FILE_NAME)
        self.parse_abbrevfile(afi)
        afi.close()

    def get_weight (self, filename=None):
        if filename:
            wfi = open(filename,'r')
        else:
            wfi = self.get_file_from_url(self.WEIGHT_FILE_NAME)
        self.parse_weightfile(wfi)
        wfi.close()

    def grab_data (self, directory=None):
        self.db.changed = True
        self.get_abbrev((isinstance(directory,str)
                         and
                         os.path.join(directory,self.ABBREV_FILE_NAME)))
        self.get_weight((isinstance(directory,str)
                         and
                         os.path.join(directory,self.WEIGHT_FILE_NAME)))

    def parse_line (self, line, field_defs, split_on='^'):
        """Handed a line and field definitions, return a dictionary of
        the line parsed.

        The line is a line with fields split on '^'

        field_defs is a list of entries for each field in our data.
        [(long_name,short_name,type),(long_name,short_name,type),...]

        Our dictionary will be in the form:

        {short_name : value,
         short_name : value,
         ...}
        """
        d = {}
        fields = line.split("^")
        for n,fl in enumerate(fields):
            lname,sname,typ = field_defs[n]
            if fl and fl[0]=='~' and fl[-1]=='~':
                d[sname]=fl[1:-1]
            if typ=='float':
                try:
                    d[sname]=float(d.get(sname,fl))
                except:
                    d[sname]=None
            elif typ=='int':
                try:
                    d[sname]=int(d.get(sname,fl))
                except:
                    if d.get(sname,fl):
                        print d.get(sname,fl),'is not an integer'
                        raise
                    # If it's nothing, we don't bother...
                    if d.has_key(sname): del d[sname]                    
        return d

    def parse_abbrevfile (self, abbrevfile):
        if self.show_progress:
            self.show_progress(float(0.03),_('Parsing nutritional data...'))
        self.datafile = tempfile.TemporaryFile()
        ll=abbrevfile.readlines()
        tot=len(ll)
        n = 0
        for n,l in enumerate(ll):
            tline=TimeAction('1 line iteration',0)            
            t=TimeAction('split fields',0)
            d = self.parse_line(l,NUTRITION_FIELDS)
            fields = l.split("^")
            d['desc']=expand_abbrevs(d['desc'])
            for i in FOOD_GROUPS:
                if 1000+i > d['ndbno'] >= i:
                    d['foodgroup']=FOOD_GROUPS[i]
                    break
            t.end()
            if self.show_progress and n % 50 == 0:
                self.show_progress(float(n)/tot,_('Reading nutritional data: imported %s of %s entries.')%(n,tot))
            t = TimeAction('append to db',0)
            try:
                self.db.nview.append(d)
            except:
                print 'Error appending',d,'to nview'
                raise
            t.end()                                
            tline.end()

    def parse_weightfile (self, weightfile):
        if self.show_progress:
            self.show_progress(float(0.03),_('Parsing weight data...'))
        ll=weightfile.readlines()
        tot=len(ll)
        n=0
        for n,l in enumerate(ll):
            if self.show_progress and n % 50 == 0:
                self.show_progress(
                    float(n)/tot,
                    _('Reading weight data for nutritional items: imported %s of %s entries')%(n,tot)
                    )
            d = self.parse_line(l,WEIGHT_FIELDS)
            if d.has_key('stdev'): del d['stdev']
            try:
                self.db.nwview.append(d)
            except:
                print "Error appending ",d,"to nwview"
                raise
            


if __name__ == '__main__':
    tot_prog = 0
    def show_prog (perc, msg):
        perc = perc * 100
        if perc - tot_prog: print "|" * int(perc - tot_prog)
    print 'getting our recipe database'
    import gourmet.recipeManager
    db = gourmet.recipeManager.RecipeManager(**gourmet.recipeManager.dbargs)
    print 'getting our grabber ready'
    grabber = DatabaseGrabber(db,show_prog)
    print 'grabbing recipes!'
    #grabber.grab_data('/home/tom/Projects/nutritional_data/')
    grabber.parse_weightfile(open('/home/tom/Projects/nutritional_data/WEIGHT.txt','r'))
    #grabber.get_weight('/home/tom/Projects/nutritional_data/WEIGHT.txt')    
    

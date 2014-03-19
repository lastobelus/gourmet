from gourmet.backends.db import Session
from gourmet.models.ingredient import order_ings
from gourmet import prefs

import gtk
import xml.sax.saxutils

class IngredientDisplay:

    """The ingredient portion of our recipe display card.
    """
    
    def __init__ (self, recipe_display, session=Session()):
        self.recipe_display = recipe_display
        self.session = session
        self.prefs = prefs.get_prefs()
        self.setup_widgets()
        self.recipe_display = recipe_display; self.rg = self.recipe_display.rg
        self.markup_ingredient_hooks = []

    def setup_widgets (self):
        self.ui = self.recipe_display.ui
        self.ingredientsDisplay = self.ui.get_object('ingredientsDisplay1')
        self.ingredientsDisplayLabel = self.ui.get_object('ingredientsDisplayLabel')
        self.ingredientsDisplay.connect('link-activated',
                                        self.show_recipe_link_cb)
        self.ingredientsDisplay.set_wrap_mode(gtk.WRAP_WORD)
        
    def update_from_database (self):
        print self.recipe_display.current_rec
        print self.recipe_display.current_rec.ingredients
        self.ing_alist = order_ings(
                            self.recipe_display.current_rec.ingredients
                         )
#         self.rg.rd.order_ings(
#             self.rg.rd.get_ings(self.recipe_display.current_rec)
#             )
        print self.ing_alist
        self.display_ingredients()

    def display_ingredients (self):
        group_strings = []
        group_index = 0
        nut_highlighted = False
        for g,ings in self.ing_alist:
            labels = []
            if g: labels.append("<u>%s</u>"%xml.sax.saxutils.escape(g))
            ing_index = 0
            for i in ings:
                ing_strs = []
                amt,unit = i.get_amount_and_unit(mult=self.recipe_display.mult,
                                                 conv=(self.prefs.get('readableUnits',True)) # and self.rg.conv or None) # FIXME
                                                 )
                #if self.nutritional_highlighting and self.yields_orig:
                #    amt,unit = self.rg.rd.get_amount_and_unit(i,
                #                                              mult = 1.0/self.yields_orig,
                #                                              conv=(self.prefs.get('readableUnits',True) and self.rg.conv or None)
                #                                              )
                if amt: ing_strs.append(amt)
                if unit: ing_strs.append(unit)
                if i.item: ing_strs.append(i.item)
                if i.optional:
                    ing_strs.append(_('(Optional)'))
                istr = xml.sax.saxutils.escape(' '.join(ing_strs))                
                if i.refid:
                    istr = ('<a href="%s:%s">'%(i.refid,
                                                xml.sax.saxutils.escape(i.item))
                             + istr
                            + '</a>')
                istr = self.run_markup_ingredient_hooks(istr,i,
                                                        ing_index,
                                                        group_index)
                labels.append(
                    istr
                    )                
                ing_index += 1
            group_strings.append('\n'.join(labels))
            group_index += 1
        label = '\n\n'.join(group_strings)
        if nut_highlighted:
            label = '<i>Highlighting amount of %s in each ingredient.</i>\n'%self.nutritionLabel.active_label+label
        if label:
            self.ingredientsDisplay.set_text(label)
            self.ingredientsDisplay.set_editable(False)
            self.ingredientsDisplay.show()
            self.ingredientsDisplayLabel.show()
        else:
            self.ingredientsDisplay.hide()
            self.ingredientsDisplayLabel.hide()        

    def run_markup_ingredient_hooks (self, ing_string, ing_obj, ing_index, group_index):
        for hook in self.markup_ingredient_hooks:
            # each hook gets the following args:
            # ingredient string, ingredient object, ingredient index, group index
            ing_string = hook(ing_string, ing_obj, ing_index, group_index)
        return ing_string

    def create_ing_alist (self):
        """Create alist ing_alist based on ingredients in DB for current_rec"""
        ings=self.rg.rd.get_ings(self.get_current_rec())
        self.ing_alist = self.rg.rd.order_ings(ings)
        debug('self.ing_alist updated: %s'%self.ing_alist,1)

    # Callbacks

    def show_recipe_link_cb (self, widg, link):
        rid,rname = link.split(':',1)
        rec = self.rg.rd.get_rec(int(rid))
        if not rec:
            rec = self.rg.rd.fetch_one(
                self.rg.rd.recipe_table,
                title=rname
                )
        if rec:
            self.rg.open_rec_card(rec)
        else:
            de.show_message(parent=self.display_window,
                            label=_('Unable to find recipe %s in database.')%rname
                            )

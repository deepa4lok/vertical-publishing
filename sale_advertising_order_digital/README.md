1. It creates a link between advertising class and advertising issues through the
   'digital' boolean. Whenever the 'digital' boolean in the advertising class is set to
   true, this module makes sure only advertising issues will be shown that have the
   'digital' boolean set to true as well.
2. This also applies vice versa: whenever the 'digital' boolean in the advertising class
   is set to false, only advertising issues will be shown that have the 'digital'
   boolean set to false.
3. This module adds an editable boolean 'Issue date >= today' in the sale advertising
   order line as well. This boolean is only applicable when the medium
   sale_advertising_order.magazine_advertising_category ('Print') is selected. The
   boolean 'Issue date >= today' is set to true by default and makes sure only
   advertising issues equal to or larger than today are selectable. The user can
   manually set the boolean 'Issue date >= today' to false to be able to select any
   advertising issue, even if it's issue date is in the past.

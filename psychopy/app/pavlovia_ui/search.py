#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2018 Jonathan Peirce
# Distributed under the terms of the GNU General Public License (GPL).

from past.builtins import basestring

from .project import DetailsPanel
from .functions import logInPavlovia

from ._base import BaseFrame
from psychopy.localization import _translate
from psychopy.projects import pavlovia

import copy
import wx
from pkg_resources import parse_version
from wx.lib import scrolledpanel as scrlpanel
import wx.lib.mixins.listctrl as listmixin

if parse_version(wx.__version__) < parse_version('4.0.0a1'):
    import wx.lib.hyperlink as wxhl
else:
    import wx.lib.agw.hyperlink as wxhl


class SearchFrame(wx.Dialog):

    def __init__(self, app, parent=None, pos=wx.DefaultPosition,
                 style=None):
        if style is None:
            style = (wx.DEFAULT_DIALOG_STYLE | wx.CENTER |
                     wx.TAB_TRAVERSAL | wx.RESIZE_BORDER)
        title = _translate("Search for projects online")
        self.frameType = 'ProjectSearch'
        wx.Dialog.__init__(self, parent, -1, title=title, style=style,
                           size=(500, 300))
        self.app = app
        self.project = None
        self.parent = parent
        self.itemDataMap = None
        # info about last search (NB None means no search but [] or '' means empty)
        self.lastSearchStr = None
        self.lastSearchOwn = None
        self.lastSearchGp = None
        self.lastSearchPub = None

        # self.mainPanel = wx.Panel(self, wx.ID_ANY)
        self.searchLabel = wx.StaticText(self, wx.ID_ANY, 'Search:')
        self.searchCtrl = wx.TextCtrl(self, wx.ID_ANY)
        self.searchCtrl.Bind(wx.EVT_BUTTON, self.onSearch)
        self.searchBtn = wx.Button(self, wx.ID_ANY, "Search")
        self.searchBtn.Bind(wx.EVT_BUTTON, self.onSearch)
        self.searchBtn.SetDefault()

        self.searchInclPublic = wx.CheckBox(self, wx.ID_ANY,
                                          label="Public")
        self.searchInclPublic.Bind(wx.EVT_CHECKBOX, self.onSearch)
        self.searchInclPublic.SetValue(True)

        self.searchInclGroup = wx.CheckBox(self, wx.ID_ANY,
                                          label="My groups")
        self.searchInclGroup.Bind(wx.EVT_CHECKBOX, self.onSearch)
        self.searchInclGroup.SetValue(True)

        self.searchBuilderOnly = wx.CheckBox(self, wx.ID_ANY,
                                             label="Only Builder")
        self.searchBuilderOnly.Bind(wx.EVT_CHECKBOX, self.onSearch)
        # then the search results
        self.searchResults = ProjectListCtrl(self)

        # on the right
        self.detailsPanel = DetailsPanel(parent=self)
        self.searchBtnSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.searchBtnSizer.Add(self.searchCtrl, 1, wx.EXPAND, 5)
        self.searchBtnSizer.Add(self.searchBtn, 0, wx.EXPAND, 5)
        self.optionsSizer = wx.WrapSizer()
        self.optionsSizer.AddMany([self.searchInclGroup, self.searchInclPublic,
                                   self.searchBuilderOnly])
        self.leftSizer = wx.BoxSizer(wx.VERTICAL)
        self.leftSizer.Add(self.searchLabel, 0, wx.EXPAND | wx.ALL, 5)
        self.leftSizer.Add(self.optionsSizer)
        self.leftSizer.Add(self.searchBtnSizer, 0, wx.EXPAND | wx.ALL, 5)
        self.leftSizer.Add(self.searchResults, 1, wx.EXPAND | wx.ALL, 5)

        self.mainSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.mainSizer.Add(self.leftSizer, 1, wx.EXPAND | wx.ALL, 5)
        self.mainSizer.Add(self.detailsPanel, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(self.mainSizer)
        if self.parent:
            self.CenterOnParent()

        # if projects == 'no user':
        #     msg = _translate("Log in to search your own projects")
        #     loginBtn = wx.Button(self, wx.ID_ANY, label=msg)
        #     loginBtn.Bind(wx.EVT_BUTTON, self.onLoginClick)

    def getSearchOptions(self):
        opts = {}
        opts['inclPublic'] = self.searchInclPublic.GetValue()
        opts['builderOnly'] = self.searchBuilderOnly.GetValue()
        opts['inclGroup'] = self.searchBuilderOnly.GetValue()
        return opts

    def onSearch(self, evt=None):
        opts = self.getSearchOptions()

        searchStr = self.searchCtrl.GetValue()
        newSearch = (searchStr!=self.lastSearchStr)
        self.lastSearchStr = newSearch

        session = pavlovia.currentSession
        # search own
        if newSearch:
            self.lastSearchOwn = session.gitlab.projects.list(owned=True, search=searchStr)

        # search my groups
        if opts['inclGroup'] and (newSearch or self.lastSearchGp is None):
            # group projects: owned=False, membership=True
            self.lastSearchGp = session.gitlab.projects.list(
                owned=False, membership=True, search=searchStr)
        elif not opts['inclGroup']:  # set to None (to indicate non-search not simply empty result)
            self.lastSearchGp = None
        elif opts['inclGroup'] and not newSearch:
            pass  # we have last search and we need it so do nothing
        else:
            print("ERROR: During Pavlovia search we found opts['inclGroup']={}, newSearch={}"
                  .format(opts['inclGroup'], newSearch))

        # search public
        if opts['inclPublic'] and (newSearch or self.lastSearchPub is None):
            self.lastSearchPub = session.gitlab.projects.list(owned=False, membership=False,
                                                              search=searchStr)
        elif not opts['inclPublic']:  # set to None (to indicate non-search not simply empty result)
            self.lastSearchPub = None
        elif opts['inclPublic'] and not newSearch:
            pass  # we have last search and we need it so do nothing
        else:
            print("ERROR: During Pavlovia search we found opts['inclPublic']={}, newSearch={}"
                  .format(opts['inclPublic'], newSearch))

        projs = copy.copy(self.lastSearchOwn)
        if opts['inclGroup']:
            projs.extend(self.lastSearchGp)
        if opts['inclPublic']:
            projs.extend(self.lastSearchPub)

        projs = getUniqueByID(projs)
        projs = [pavlovia.PavloviaProject(proj) for proj in projs if proj.id]

        self.itemDataMap = projs
        self.searchResults.setContents(projs)
        self.searchResults.Update()
        self.Layout()

    def onLoginClick(self, event):
        user = logInPavlovia(parent=self.parent)

    def Show(self):
        # show the dialog then start search
        wx.Dialog.Show(self)
        wx.Yield()
        self.onSearch()  # trigger the search update


class ProjectListCtrl(wx.ListCtrl, listmixin.ColumnSorterMixin):
    """A scrollable panel showing a list of projects. To be used within the
    Project Search dialog
    """

    def __init__(self, parent, frame=None):
        wx.ListCtrl.__init__(self, parent, wx.ID_ANY,
                             style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.parent = parent
        if frame is None:
            self.frame = parent
        else:
            self.frame = frame
        self.projList = []
        columnList = ['owner', 'name', 'description']

        # Give it some columns.
        # The ID col we'll customize a bit:
        for n, columnName in enumerate(columnList):
            self.InsertColumn(n, columnName)
        # set the column sizes *after* adding the items
        for n, columnName in enumerate(columnList):
            self.SetColumnWidth(n, wx.LIST_AUTOSIZE)

        # after creating columns we can create the sort mixin
        listmixin.ColumnSorterMixin.__init__(self, len(columnList))

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onChangeSelection)

    def setContents(self, projects):
        self.projList = []
        self.DeleteAllItems()

        for index, thisProj in enumerate(projects):
            if not hasattr(thisProj, 'id'):
                continue
            try:
                self.Append([thisProj.owner, thisProj.name,
                         thisProj.description])
            except:
                print(thisProj)
            self.projList.append(thisProj)
        # resize the columns
        for n in range(self.ColumnCount):
            self.SetColumnWidth(n, wx.LIST_AUTOSIZE_USEHEADER)
            if self.GetColumnWidth(n) > 200:
                self.SetColumnWidth(n, 200)
        self.Layout()
        self.Fit()

    def onChangeSelection(self, event):
        proj = self.projList[event.GetIndex()]
        self.frame.detailsPanel.setProject(proj)

    def GetListCtrl(self):
        return self


def getUniqueByID(seq):
    """Very fast function to remove duplicates from a list while preserving order

    Based on sort f8() by Dave Kirby
    benchmarked at https://www.peterbe.com/plog/uniqifiers-benchmark

    Requires Python>=2.7 (requires set())
    """
    # Order preserving
    seen = set()
    return [x for x in seq if x.id not in seen and not seen.add(x.id)]
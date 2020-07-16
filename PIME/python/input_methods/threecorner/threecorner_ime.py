#! python3
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from keycodes import *  # for VK_XXX constants
from textService import *
import io
import os.path
import copy

from cinbase import CinBase
from cinbase import LoadCinTable
from cinbase import LoadRCinTable
from cinbase import LoadHCinTable
from cinbase.config import CinBaseConfig

CHINESE_MODE = 1
ENGLISH_MODE = 0

class ThreeCornerTextService(TextService):

    compositionChar = ''

    def __init__(self, client):
        TextService.__init__(self, client)

        # 輸入法模組自訂區域
        self.imeDirName = "threecorner"
        self.maxCharLength = 6 # 輸入法最大編碼字元數量
        self.cinFileList = ["threecorner.json"]

        self.cinbase = CinBase
        self.curdir = os.path.abspath(os.path.dirname(__file__))

        # 初始化輸入行為設定
        self.cinbase.initTextService(self, TextService)

        # 載入用戶設定值
        CinBaseConfig.__init__()
        self.configVersion = CinBaseConfig.getVersion()
        self.cfg = copy.deepcopy(CinBaseConfig)
        self.cfg.imeDirName = self.imeDirName
        self.cfg.cinFileList = self.cinFileList
        self.cfg.load()
        self.jsondir = self.cfg.getJsonDir()
        self.cindir = self.cfg.getCinDir()
        self.ignorePrivateUseArea = self.cfg.ignorePrivateUseArea
        self.cinbase.initCinBaseContext(self)
        self.useMagicKey = False


        # 載入輸入法碼表
        if not CinTable.curCinType == self.cfg.selCinType and not CinTable.loading:
            loadCinFile = LoadCinTable(self, CinTable)
            loadCinFile.start()
        else:
            while CinTable.loading:
                continue
            self.cin = CinTable.cin


    # 檢查設定檔是否有被更改，是否需要套用新設定
    def checkConfigChange(self):
        self.cinbase.checkConfigChange(self, CinTable, RCinTable, HCinTable)


    # 輸入法被使用者啟用
    def onActivate(self):
        TextService.onActivate(self)
        self.cinbase.onActivate(self)


    # 使用者離開輸入法
    def onDeactivate(self):
        TextService.onDeactivate(self)
        self.cinbase.onDeactivate(self)


    # 使用者按下按鍵，在 app 收到前先過濾那些鍵是輸入法需要的。
    # return True，系統會呼叫 onKeyDown() 進一步處理這個按鍵
    # return False，表示我們不需要這個鍵，系統會原封不動把按鍵傳給應用程式
    def filterKeyDown(self, keyEvent):
        KeyState = self.cinbase.filterKeyDown(self, keyEvent, CinTable, RCinTable, HCinTable)
        if keyEvent.isKeyToggled(VK_NUMLOCK) and keyEvent.keyCode == VK_DECIMAL:
            return True
        if keyEvent.isKeyToggled(VK_NUMLOCK) and keyEvent.keyCode >= VK_NUMPAD0 and keyEvent.keyCode <= VK_DIVIDE and self.langMode == CHINESE_MODE and not self.tempEnglishMode:
            return True
        if keyEvent.keyCode == VK_RETURN and not self.showCandidates and (self.langMode == CHINESE_MODE and len(self.compositionChar) >= 1 and not self.menumode) or (self.tempEnglishMode and self.isComposing()) and not self.showmenu:
            while len(self.compositionChar) < self.maxCharLength and self.compositionChar != "":
                self.compositionChar += str(0)
            return True
        
        return KeyState


    def onKeyDown(self, keyEvent):
        # Num鍵盤對映
        candidates = []
        if keyEvent.isKeyToggled(VK_NUMLOCK) and keyEvent.keyCode >= VK_NUMPAD0 and keyEvent.keyCode <= VK_DIVIDE and self.langMode == CHINESE_MODE and not self.tempEnglishMode:
            charStr = chr(keyEvent.keyCode-48)
            if self.isShowCandidates and self.isInSelKeys(self, keyEvent.keyCode-48) and not keyEvent.isKeyDown(VK_SHIFT): # 使用選字鍵執行項目或輸出候選字
                if self.selKeys.index(charStr) < self.candPerPage and self.selKeys.index(charStr) < len(self.candidateList):
                    # print("選字", charStr, self.selKeys.index(charStr))
                    candCursor = self.selKeys.index(charStr)
                    itemName = self.candidateList[candCursor]
                    self.switchmenu = True
                    i = self.selKeys.index(charStr)
                    if i < self.candPerPage and i < len(self.candidateList):
                        commitStr = self.candidateList[i]
                        self.lastCommitString = commitStr
                        self.setOutputString(self, RCinTable, commitStr)
                        if self.showPhrase and not self.selcandmode:
                            self.phrasemode = True
                        self.resetComposition(self)
                        candCursor = 0
                        currentCandPage = 0
            #  組字字根超過最大值
            elif len(self.compositionChar) >= self.maxCharLength:
                if self.cin.isInKeyName(self.compositionChar[len(self.compositionChar)-1:]):
                    keyLength = len(self.cin.getKeyName(self.compositionChar[len(self.compositionChar)-1:]))
                else:
                    keyLength = 1
                if self.compositionBufferMode:
                    self.removeCompositionBufferString(self, keyLength, False)
                else:
                    self.setCompositionString(self.compositionString[:-keyLength])
                self.compositionChar = self.compositionChar[:-1]
            elif not keyEvent.isKeyDown(VK_SHIFT) and not keyEvent.isKeyDown(VK_CONTROL):
                if keyEvent.keyCode == VK_DECIMAL:
                    self.compositionChar += "*"
                    self.useMagicKey = True
                else:
                    self.compositionChar += charStr
                if self.compositionBufferMode:
                    self.cinbase.setCompositionBufferString(self, self.compositionChar, 0)
                else:
                    self.setCompositionString(self.compositionChar)
                if (self.langMode == CHINESE_MODE and len(self.compositionChar) >= 1 and not self.menumode) or (self.tempEnglishMode and self.isComposing()):
                    # 載入輸入法碼表
                    try:
                        if self.cin.isInCharDef(self.compositionChar):                    
                            candidates = self.cin.getCharDef(self.compositionChar)
                    except:
                        if not CinTable.curCinType == self.cfg.selCinType and not CinTable.loading:
                            loadCinFile = LoadCinTable(self, CinTable)
                            loadCinFile.start()
                        else:
                            while CinTable.loading:
                                continue
                            self.cin = CinTable.cin
                            if self.cin.isInCharDef(self.compositionChar):                    
                                candidates = self.cin.getCharDef(self.compositionChar)
                    print("候選字", candidates)
                        # 字滿及符號處理 (大易、注音、輕鬆)
                    if len(self.compositionChar) == self.maxCharLength:
                        if self.useMagicKey:
                            candidates = self.cin.getWildcardCharDefs(self.compositionChar, "*", 9)
                        if candidates and not self.phrasemode:
                            if len(candidates) > 1:
                                self.setCandidateList(candidates)
                                self.setShowCandidates(True)
                                self.canSetCommitString = False
                                self.isShowCandidates = True
                                self.useMagicKey = False
                            else:
                                commitStr = candidates[0]
                                self.lastCommitString = commitStr
                                self.setOutputString(self, RCinTable, commitStr)
                                if self.showPhrase and not self.selcandmode:
                                    self.phrasemode = True
                                self.resetComposition(self)
                                candCursor = 0
                                currentCandPage = 0
                                self.canSetCommitString = True
                                self.isShowCandidates = False
                                self.useMagicKey = False
                            return True
        # 如果數字不滿，則後面補零
        if keyEvent.keyCode == VK_RETURN and not self.showCandidates and (self.langMode == CHINESE_MODE and len(self.compositionChar) >= 1 and not self.menumode) or (self.tempEnglishMode and self.isComposing()) and not self.showmenu:
            # while len(self.compositionChar) < self.maxCharLength and self.compositionChar != "":
                # self.compositionChar += str(0)
            # 載入輸入法碼表
            try:
                if self.useMagicKey:
                    candidates = self.cin.getWildcardCharDefs(self.compositionChar, "*", 9)
                elif self.cin.isInCharDef(self.compositionChar):                    
                    candidates = self.cin.getCharDef(self.compositionChar)
            except:
                if not CinTable.curCinType == self.cfg.selCinType and not CinTable.loading:
                    loadCinFile = LoadCinTable(self, CinTable)
                    loadCinFile.start()
                else:
                    while CinTable.loading:
                        continue
                    self.cin = CinTable.cin
                    if self.useMagicKey:
                        candidates = self.cin.getWildcardCharDefs(self.compositionChar, "*", 9)
                    elif self.cin.isInCharDef(self.compositionChar):                    
                        candidates = self.cin.getCharDef(self.compositionChar)
            print("候選字", candidates)
            if candidates and not self.phrasemode:
                if len(candidates) > 1:
                    self.setCandidateList(candidates)
                    self.setShowCandidates(True)
                    self.canSetCommitString = False
                    self.isShowCandidates = True
                    self.useMagicKey = False
                else:
                    commitStr = candidates[0]
                    self.lastCommitString = commitStr

                    self.setOutputString(self, RCinTable, commitStr)
                    if self.showPhrase and not self.selcandmode:
                        self.phrasemode = True
                    self.resetComposition(self)
                    candCursor = 0
                    currentCandPage = 0
                    self.canSetCommitString = True
                    self.isShowCandidates = False
                    self.useMagicKey = False
                return True
                    # if not self.isShowCandidates:
                    #     if self.compositionBufferMode:
                    # if not len(self.compositionChar) == 1:
                        
                        # if len(candidates) > 1:
                        #     self.isShowCandidates = True
                        #     self.canUseSelKey = True
                        #     self.canSetCommitString = True
                        #     self.setCandidateList(candidates)
                        #     self.setShowCandidates(True)
                        # else:
                        #     commitStr = candidates[0]
                        #     self.lastCommitString = commitStr
                        #     self.setOutputString(self, RCinTable, commitStr)
                        #     if self.showPhrase and not self.selcandmode:
                        #         self.phrasemode = True
                        #     self.resetComposition(self)
                        #     candCursor = 0
                        #     currentCandPage = 0
                        #     self.canSetCommitString = True
                        #     self.isShowCandidates = True
                        # # else:
                        #     self.isShowCandidates = True
                        #     self.canUseSelKey = True
        KeyState = self.cinbase.onKeyDown(self, keyEvent, CinTable, RCinTable, HCinTable)
        return KeyState


    # 使用者放開按鍵，在 app 收到前先過濾那些鍵是輸入法需要的。
    # return True，系統會呼叫 onKeyUp() 進一步處理這個按鍵
    # return False，表示我們不需要這個鍵，系統會原封不動把按鍵傳給應用程式
    def filterKeyUp(self, keyEvent):
        KeyState = self.cinbase.filterKeyUp(self, keyEvent)
        return KeyState


    def onKeyUp(self, keyEvent):
        self.cinbase.onKeyUp(self, keyEvent)


    def onPreservedKey(self, guid):
        KeyState = self.cinbase.onPreservedKey(self, guid)
        return KeyState


    def onCommand(self, commandId, commandType):
        self.cinbase.onCommand(self, commandId, commandType)


    # 開啟語言列按鈕選單
    def onMenu(self, buttonId):
        MenuItems = self.cinbase.onMenu(self, buttonId)
        return MenuItems


    # 鍵盤開啟/關閉時會被呼叫 (在 Windows 10 Ctrl+Space 時)
    def onKeyboardStatusChanged(self, opened):
        TextService.onKeyboardStatusChanged(self, opened)
        self.cinbase.onKeyboardStatusChanged(self, opened)


    # 當中文編輯結束時會被呼叫。若中文編輯不是正常結束，而是因為使用者
    # 切換到其他應用程式或其他原因，導致我們的輸入法被強制關閉，此時
    # forced 參數會是 True，在這種狀況下，要清除一些 buffer
    def onCompositionTerminated(self, forced):
        TextService.onCompositionTerminated(self, forced)
        self.cinbase.onCompositionTerminated(self, forced)


    # 設定候選字頁數
    def setCandidatePage(self, page):
        self.currentCandPage = page

    # 判斷選字鍵?
    def isInSelKeys(self, cbTS, charCode):
        for key in cbTS.selKeys:
            if ord(key) == charCode:
                return True
        return False

    # 重置輸入的字根
    def resetComposition(self, cbTS):
        cbTS.compositionChar = ''
        if not cbTS.compositionBufferMode:
            cbTS.setCompositionString('')
        cbTS.isShowCandidates = False
        cbTS.setCandidateCursor(0)
        cbTS.setCandidatePage(0)
        cbTS.setCandidateList([])
        cbTS.setShowCandidates(False)
        cbTS.wildcardcandidates = []
        cbTS.wildcardpagecandidates = []
        cbTS.menumode = False
        cbTS.multifunctionmode = False
        cbTS.menusymbolsmode = False
        cbTS.ctrlsymbolsmode = False
        cbTS.fullsymbolsmode = False
        cbTS.dayisymbolsmode = False
        cbTS.keepComposition = False
        cbTS.homophonemode = False
        cbTS.homophoneselpinyinmode = False
        cbTS.homophoneChar = ''
        cbTS.homophoneStr = ''
        cbTS.isHomophoneChardefs = False
        cbTS.homophonecandidates = []
        cbTS.selcandmode = False
        cbTS.lastCompositionCharLength = 0

    def setOutputString(self, cbTS, RCinTable, commitStr):
        # 如果使用萬用字元解碼
        if cbTS.isWildcardChardefs:
            if not cbTS.client.isUiLess:
                cbTS.isShowMessage = True
                cbTS.showMessageOnKeyUp = True
                cbTS.onKeyUpMessage = cbTS.cin.getCharEncode(commitStr)
            cbTS.wildcardcandidates = []
            cbTS.wildcardpagecandidates = []
            cbTS.isWildcardChardefs = False

        if cbTS.imeReverseLookup:
            if RCinTable.cin is not None:
                if not RCinTable.cin.getCharEncode(commitStr) == "":
                    if not cbTS.client.isUiLess:
                        cbTS.isShowMessage = True
                        message = RCinTable.cin.getCharEncode(commitStr)
                        if not cbTS.client.isMetroApp:
                            cbTS.showMessageOnKeyUp = True
                            cbTS.onKeyUpMessage = message
                        else:
                            cbTS.showMessage(message, cbTS.messageDurationTime)
            else:
                if not cbTS.client.isUiLess:
                    cbTS.isShowMessage = True
                    cbTS.showMessageOnKeyUp = True
                    if cbTS.RCinFileNotExist:
                        cbTS.onKeyUpMessage = "反查字根碼表檔案不存在！"
                    else:
                        cbTS.onKeyUpMessage = "反查字根碼表尚在載入中！"

        if cbTS.homophoneQuery and cbTS.isHomophoneChardefs:
            cbTS.isHomophoneChardefs = False
            if not cbTS.client.isUiLess:
                cbTS.isShowMessage = True
                cbTS.showMessageOnKeyUp = True
                cbTS.onKeyUpMessage = cbTS.cin.getCharEncode(commitStr)

        # 如果使用打繁出簡，就轉成簡體中文
        if cbTS.outputSimpChinese:
            commitStr = cbTS.opencc.convert(commitStr)

        if not cbTS.compositionBufferMode:
            cbTS.setCommitString(commitStr)
        else:
            RemoveStringLength = 0
            if not cbTS.selcandmode:
                if cbTS.menusymbolsmode:
                    RemoveStringLength = len(cbTS.compositionChar) - 1
                    cbTS.menusymbolsmode = False
                elif cbTS.dayisymbolsmode:
                    RemoveStringLength = self.calcRemoveStringLength(cbTS) - 1
                else:
                    RemoveStringLength = self.calcRemoveStringLength(cbTS)
            else:
                self.removeCompositionBufferString(cbTS, 1, False if cbTS.compositionBufferCursor < len(cbTS.compositionBufferString) else True)
            self.setCompositionBufferString(cbTS, commitStr, RemoveStringLength)
            if not cbTS.selcandmode:
                strLength = len(commitStr)
                if strLength > 1:
                    for cStr in commitStr:
                        strLength -= 1
                        if cbTS.compositionBufferType == "msymbols":
                            cChar = cbTS.compositionChar[commitStr.index(cStr)] if cbTS.compositionChar[0] != "`" else cbTS.compositionChar[commitStr.index(cStr) + 1]
                            self.setCompositionBufferChar(cbTS, cbTS.compositionBufferType, cChar, cbTS.compositionBufferCursor - strLength)
                        else:
                            self.setCompositionBufferChar(cbTS, cbTS.compositionBufferType, cbTS.compositionChar, cbTS.compositionBufferCursor - strLength)
                else:
                    self.setCompositionBufferChar(cbTS, cbTS.compositionBufferType, cbTS.compositionChar, cbTS.compositionBufferCursor)

class CinTable:
    loading = False
    def __init__(self):
        self.cin = None
        self.curCinType = None
        self.userExtendTable = None
        self.priorityExtendTable = None
        self.ignorePrivateUseArea = None
CinTable = CinTable()


class RCinTable:
    loading = False
    def __init__(self):
        self.cin = None
        self.curCinType = None
RCinTable = RCinTable()


class HCinTable:
    loading = False
    def __init__(self):
        self.cin = None
        self.curCinType = None
HCinTable = HCinTable()

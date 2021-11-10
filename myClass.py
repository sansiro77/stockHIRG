import pandas as pd
import time
import datetime
import requests
import os
import calendar
import math
from chinese_calendar import is_workday
from functools import partial
import copy
import numpy as np
import csv

GoodIndex = 1
BadIndex = 0

EmptyDataPath = '/Users/desmond/Famliy/Liu/Final/DataForTest/'

RawDataPath = '/Users/desmond/Famliy/Liu/Final/NewLi/'
#RawDataPath = '/Volumes/wdf_backup/NewLi/'
AllStockPath = '/Users/desmond/Famliy/Liu/Final/ParamterTest/'
SCIStockPath = '/Users/desmond/Famliy/Liu/Final/BaseTest/'
CompCodePath = '/Users/desmond/Famliy/Liu/Final/PlateIndex/'#ComponentStockCode'

AllPlateIndexList = ['881166','881153','881157','881155','885403','885525','885431']


SourcePath = os.getcwd() 
#SCIStockPath = '/storage/fdunphome/liyian/LiPyData/SCIdata/'
#EmptyDataPath = '/storage/fdunphome/liyian/LiStock/ClassNeed/'
#RawDataPath = '/storage/fdunphome/liyian/LiPyData/'
#CompCodePath = '/storage/fdunphome/liyian/LiStock/ClassNeed/'#ComponentStockCode
#AllCSVPath = '/storage/fdunphome/liyian/LiPyData/All/'
#AllPlateIndexList = ['881166','881153','881157','881155','885403','885525','885431']

#EmptyDataPath = '/storage/fdunphome/wangdongfang/liyian/QTTest/DataForTest/'
#RawDataPath = '/storage/fdunphome/wangdongfang/liyian/QTTest/DataForTest/'
#AllStockPath = '/storage/fdunphome/wangdongfang/liyian/QTTest/'

#EmptyDataPath = '/storage/fdunphome/wangdongfang/liyian/QTTest/D2Test/'
#RawDataPath = '/storage/fdunphome/wangdongfang/liyian/QTTest/D2Test/'
#AllStockPath = '/storage/fdunphome/wangdongfang/liyian/QTTest/'


CONST_DayStep = 48
CONST_BeginHourMin = 1330
CONST_EndHourMin = 1450
CONST_InitLastDayDecMin = 0.01

OperatThres = 0.01  # a%
CONST_InitDay = 2                      # use 3 day data to init
CONST_OscilMinCount = 2
CONST_LowLimitP = 1
CONST_UpLimitP = 200

CONST_InitLastDayUnit = 3
CONST_GenearalUnit = 1
#CONST_InitLastDayHands = 1
CONST_OneHourStep = 12
CONST_LiNewUnit = 1
CONST_FinalScreenBUYCut = 2
CONST_FinalScreenSELLCut = 2
GlobalVar_MoneyToCalHandsInUnit = 200
CONST_NewLiRateListLength = 5
BUYIndex = 0
SELLIndex = 1
MergeStep = 4
FATAL_ERROR = -999
class SCIClass:
    def __init__(self):
        self.SCode = 'sh.000001'
        # 2016-01-29 15:00 end!
        self.SCILastIndex = 2737.6
    def ReturnIndexUpAndDown(self,ThisTimeIndex):
        if(self.SCILastIndex == 0):
            return 0.
        return float(ThisTimeIndex/self.SCILastIndex) - 1.
    def UpdateLastIndex(self,ThisTimeIndex):
        self.SCILastIndex = ThisTimeIndex
#---------------------------------------------------------------------------------------------------------------------------
class MyAccount:
    def __init__(self,StockIndexList,DateList):
        self.MyCash = 50000.
        self.MyHoldValue = 0.
        self.MyHowManyStock = len(StockIndexList)
        self.MyStockIndexList = StockIndexList
        self.MyOperaDateList = DateList
        self.MyTotalOperaDay = len(DateList)
        self.MyStockClass = []
        for SIndex in range(len(StockIndexList)):
            tmpClass = UnitStock(StockIndexList[SIndex])
            #print("init ",tmpClass.SCode)
            TmpPlateIndex = tmpClass.FindPlateIndex()
            if(TmpPlateIndex=='None'):
                continue
            tmpClass.SPlateIndex = TmpPlateIndex
            #tmpClass.FindPlateIndex()
            self.MyStockClass.append(tmpClass)
        self.MyTodayIndex = 0
        self.MyBuyB = 0.
        self.MySellA = 0.

        # new Li
        self.MyLastDayAsset = 0.
        self.MyLastDayHoldValue = 0.
        self.MyLastSCIIndex = 0.
        self.IsBlanace = BadIndex
        self.ExcDay = 0
    def ReutrnLastSCIRate(self,SCIIndex):
        return SCIIndex/self.MyLastSCIIndex - 1.
    def UpdateMyLastDayHoldValue(self,HoldV):
        self.MyLastDayHoldValue = HoldV
    def ReturnMyAssetInLastDay(self):
        # only work in the beginning of the day!
        return self.MyLastDayHoldValue + self.MyCash
    def DeductFromCash(self,cost):
        self.MyCash -= cost
    def AddToCash(self,MoneyFromSell):
        self.MyCash += MoneyFromSell
    def UpdateMyBuyB(self,BInLoop):
        self.MyBuyB = BInLoop
    def UpdateMySellA(self,AInLoop):
        self.MySellA = AInLoop  
    def UpdateMyTodayIndex(self,iday):
        self.MyTodayIndex = iday
    def InitNewDay(self):
        for SIndex in range(self.MyHowManyStock):
            self.MyStockClass[SIndex].STodayBuyHands = 0
    def ReturnInPoolCount(self):
        TmpInPool = 0
        for SIndex in range(self.MyHowManyStock):
            if(self.MyStockClass[SIndex].isInPool == GoodIndex):
                TmpInPool += 1
        return TmpInPool
    def EndOfDay(self,iday):
        print("length ",self.MyHowManyStock,len(self.MyStockClass),self.MyOperaDateList[iday])
        TmpHoldValue = 0.
        SingleSCIInfo = ReadSCICSVFile(self.MyOperaDateList[iday])
        self.MyLastSCIIndex = SingleSCIInfo['end'][CONST_DayStep-1]
        for SIndex in range(self.MyHowManyStock):
            #print("begin SIndex",SIndex,self.MyStockClass[SIndex].SCode)
            #---------------------------------------------------------------------------------------------------------------------------
            # part1: update in or out pool index & able to sell hands for next day.
            #---------------------------------------------------------------------------------------------------------------------------
            # change out-pool to in-pool
            if(self.MyStockClass[SIndex].isInPool == BadIndex \
            and self.MyStockClass[SIndex].STodayBuyHands != 0 \
            and self.MyStockClass[SIndex].SPlateIndex != 'None'):
                #print("Endday init ",self.MyStockClass[SIndex].SCode)
                self.MyStockClass[SIndex].isInPool = GoodIndex
            self.MyStockClass[SIndex].SAbleToSellHands += self.MyStockClass[SIndex].STodayBuyHands
            # change in-pool to out-pool
            if(self.MyStockClass[SIndex].SAbleToSellHands == 0):
                self.MyStockClass[SIndex].isInPool = BadIndex
            #---------------------------------------------------------------------------------------------------------------------------
            # part2: update LastDayLastStepPrice/LastPlateValue after all today trade.
            #---------------------------------------------------------------------------------------------------------------------------
            # Must have this stock
            SingleStockInfo = ReCSV(self.MyOperaDateList[iday],self.MyStockClass[SIndex].SCode)
            if(len(SingleStockInfo) == 0):
                continue
            TmpTodayLastPrice = SingleStockInfo['close'][CONST_DayStep-1]
            self.MyStockClass[SIndex].UpdateLastDayLastStepPrice(TmpTodayLastPrice)
            TmpHoldValue += self.MyStockClass[SIndex].ReturnAssetInLastStep()
            #print("TmpHoldValue ",TmpHoldValue)
            # Must have plate index and update it
            if(self.MyStockClass[SIndex].SPlateIndex == 'None'):
                continue
            SinglePlateInfo = RePlateCSV(self.MyOperaDateList[iday],self.MyStockClass[SIndex].SPlateIndex)
            if(len(SinglePlateInfo) == 0):
                continue
            TmpTodayLastPlateIndex = SinglePlateInfo['end'][CONST_DayStep-1]
            #print("TmpTodayLastPlateIndex ",TmpTodayLastPlateIndex,len(SinglePlateInfo))
            self.MyStockClass[SIndex].UpdateLastPlateValue(TmpTodayLastPlateIndex) 
            # update SBase label in order to include more stock
            if(self.MyStockClass[SIndex].SBase == BadIndex and \
                TmpTodayLastPrice !=0 and TmpTodayLastPlateIndex!=0):
                self.MyStockClass[SIndex].SBase = GoodIndex
            #print("end tmp ",SIndex,self.MyStockClass[SIndex].SCode) 
        self.UpdateMyLastDayHoldValue(TmpHoldValue)
        #print("end endday")

#---------------------------------------------------------------------------------------------------------------------------
class UnitStock:
    InitCut = 0.01
    OperCut = 2
    SaveDays = 3

    def __init__(self, StockIndexStr):
        self.SCode      = StockIndexStr
        self.SPlateIndex = 'None'
        self.SHandsInUnit = 0
        # self.SPrice     = np.array([])
        # self.SHands     = np.array([])
        # self.GoodCount  = np.array([]) # number of operations that satisfy the cuts
        self.SPriceAverageList = np.array([],dtype=np.float)
        self.SPriceMaxList   = np.array([],dtype=np.float)
        self.SPriceMinList   = np.array([],dtype=np.float)
        self.SOscilIncreCount = np.array([],dtype=np.float)
        self.SOscilDecreCount = np.array([],dtype=np.float)
        self.STodayInitBuy      = np.array([],dtype=np.int)
        # # e.g. total 5 hands, save SHistoryBuyPrice = [3.4]; SHistoryBuyHands = [5]
        self.SHistoryBuyPrice = np.array([],dtype=np.float)
        self.SHistoryBuyHands = np.array([],dtype=np.int)
        # e.g. total 5 hands, save S1DHistoryBuyPrice = [3.4,3.4,3.4,3.4,3.4]
        # self.S1DHistoryBuyPrice = np.array([],dtype=np.float)
        #self.STodayBuyPrice = np.array([],dtype=np.float)
        #self.STodayBuyHands = np.array([],dtype=np.int)
        self.STodayBuyHands = 0
        self.SAbleToSellHands = 0

        
        self.SUnit = 0  # total unit, include how much we can sell
        
        # self.SCurrentPrice  = np.array([])
        # self.SBuyTodayIndex = 0
        # self.maxSell  = 0
        self.isInit   = BadIndex
        self.isInPool = BadIndex
        #---------------------------------------------------------------------------------------------------------------------------
        self.SLastStepPrice = 0.
        self.STodayProfit = 0.
        self.SExperiencedHowManyDay = 0
        #---------------------------------------------------------------------------------------------------------------------------
        # 8.19 Li new idea
        self.SHistoryPlateValue = np.array([],dtype=np.float)
        self.SBase = BadIndex   # have last day end price/plate index!
        self.SLastBuyPrice = 0.
        self.SLastPlateValue = 0.
        self.SLastDayLastStepPrice = 0.
        self.SCurrentPlateIndex = 0.
        self.SInitCost = 0.
    #---------------------------------------------------------------------------------------------------------------------------
    def FindPlateIndex(self):
        for PlateType in range(len(AllPlateIndexList)):
            CompCode = pd.read_csv(CompCodePath + 'ComponentStockCode_' + AllPlateIndexList[PlateType] +'.csv', converters={'code': lambda x: str(x)})
            for i in range(len(CompCode)):
                if(CompCode['code'][i]==self.SCode[3:9]):
                    return AllPlateIndexList[PlateType]
                    #self.SPlateIndex = AllPlateIndexList[PlateType]
        return 'None' 
    #def IsInPlateOrNot(self):
    def UpdateInitCost(self,cost):
        self.SInitCost = cost
    def ReturnInitCost(self):
        return self.SInitCost
    #---------------------------------------------------------------------------------------------------------------------------
    def PrintStockCode(self):
        return self.SCode
    def PrintStockMax(self):
        return self.SPriceMaxList
    def UpdateExperiencedDay(self):
        self.SExperiencedHowManyDay += 1
        return
    def ClearExperiencedDay(self):
        self.SExperiencedHowManyDay = 0
        return
    def UpdateLastPlateValue(self,PlateEndValue):
        self.SLastPlateValue = PlateEndValue
    def UpdateLastBuyPrice(self,price):
        self.SLastBuyPrice = price
    def ReturnLastSPRate(self,price):
        # wdf_last: in history list or last day last time point end price!
        oldprice = 0.
        if(self.SHistoryBuyPrice != []):
            oldprice = self.SHistoryBuyPrice[-1]
        else:
            oldprice = self.SLastDayLastStepPrice
        return float(price/oldprice) - 1.
    def ReturnLastPIRate(self,CurrentIndex):
        oldPlateValue = 0.
        if(self.SHistoryPlateValue != []):
            oldPlateValue = self.SHistoryPlateValue[-1]
        else:
            oldPlateValue = self.SLastPlateValue
        return float(CurrentIndex/oldPlateValue) - 1.
    def ReturnRelativeRate(self,price,PlateValue,BuyOrSell):
        # relative rate consist of 3 part!
        # A: current price/last save price(in history list or last day last time point end price!) - 1
        # B: current plate index/last plate index(last day last time point) - 1
        # C: Appendix value determined by the current unit of this stock!
        TmpReRate = self.ReturnLastSPRate(price) \
                    - self.ReturnLastPIRate(PlateValue) \
                    + ReturnAppValueInTable(self.SUnit,BuyOrSell)
        return TmpReRate
    def UpdateLastDayLastStepPrice(self,price):
        self.SLastDayLastStepPrice = price
    def ReturnAssetInLastStep(self):
        return self.SLastDayLastStepPrice * self.SAbleToSellHands
    #---------------------------------------------------------------------------------------------------------------------------
    def UpdateHandsInUnit(self,HandsInUnit):
        #print("UpdateHandsInUnit",self.SCode,HandsInUnit)
        self.SHandsInUnit = HandsInUnit
    def ClearInitState(self):
        self.isInit = BadIndex
    def ReturnInitState(self):
        return self.isInit
    def ReturnInPoolOrNot(self):
        return self.isInPool
    def UpdateInPoolOrNot(self):
        if(self.SAbleToSellHands!=0 and self.isInit==GoodIndex):
            self.isInPool = GoodIndex
        else:
            self.isInPool = BadIndex
    def ChangePoolLabel(self,Index):
        self.isInPool = Index
    def ClearInitBuy(self):
        #print("ClearInitBuy()")
        self.SHandsInUnit = 0
        self.SPriceAverageList = np.array([],dtype=np.float)
        self.SPriceMaxList   = np.array([],dtype=np.float)
        self.SPriceMinList   = np.array([],dtype=np.float)
        self.SOscilIncreCount = np.array([],dtype=np.float)
        self.SOscilDecreCount = np.array([],dtype=np.float)
        self.STodayInitBuy      = np.array([],dtype=np.int)
        self.SHistoryBuyPrice = np.array([],dtype=np.float)
        self.SHistoryBuyHands = np.array([],dtype=np.int)
        self.STodayBuyHands = 0
        self.SAbleToSellHands = 0
        self.isInit   = BadIndex
        self.isInPool = BadIndex
    #---------------------------------------------------------------------------------------------------------------------------
    # buy or sell 
    #---------------------------------------------------------------------------------------------------------------------------
    def ClearTodayBuy(self):
        self.STodayBuyHands = 0
        self.ClearTodayProfit()
    def ClearTodayProfit(self):
        self.STodayProfit = 0.
    def UpdateAbleToSellHands(self):
        #print("UpdateAbleToSellHands",self.SCode,self.STodayBuyHands,self.SAbleToSellHands)
        self.SAbleToSellHands += self.STodayBuyHands
    def ReturnSumOfHistoryPrice(self):
        TmpSumPrice = 0.
        for i in range(len(self.SHistoryBuyPrice)):
            TmpSumPrice += self.SHistoryBuyPrice[i] * self.SHistoryBuyHands[i]
        return TmpSumPrice
    def ReturnCurrentValue(self):
        #print("self.SAbleToSellHands",self.SAbleToSellHands,self.SLastStepPrice)
        return self.SLastStepPrice * self.SAbleToSellHands
    def RecordLastPrice(self,LastPrice):
        self.SLastStepPrice = LastPrice
    #---------------------------------------------------------------------------------------------------------------------------  
    def GenearalNewLiBuyStock(self,BuyPrice,PlateValue):
        TotalHands = self.SHandsInUnit * CONST_LiNewUnit
        # this case is for this the first time buy!
        # wdf_last: remember STodayBuyHands should be update in the end of day
        self.SHistoryBuyPrice = np.append(self.SHistoryBuyPrice,BuyPrice)
        self.SHistoryBuyHands = np.append(self.SHistoryBuyHands,TotalHands)
        self.SHistoryPlateValue = np.append(self.SHistoryPlateValue,PlateValue)
        self.STodayBuyHands += TotalHands
        self.SUnit += CONST_LiNewUnit
        CostMoney = BuyPrice * TotalHands
        return CostMoney
    #---------------------------------------------------------------------------------------------------------------------------
    def GenearalNewLiSellStock(self,SellPrice):
        GetHowManyMoney = 0
        # in case this stock can not sell, but it never happend in here?
        # At before, this case is continue
        if(self.SAbleToSellHands == 0 \
            or self.isInPool == BadIndex):
            return GetHowManyMoney
        # get price and hands
        TmpEarlyPrice = self.SHistoryBuyPrice[-1]
        TmpHands = self.SHistoryBuyHands[-1]
        GetHowManyMoney = TmpEarlyPrice * TmpHands
        # update able to sell hands and history price
        self.SAbleToSellHands -= TmpHands
        self.SHistoryBuyPrice = np.delete(self.SHistoryBuyPrice,-1,None)
        self.SHistoryBuyHands = np.delete(self.SHistoryBuyHands,-1,None)
        self.SHistoryPlateValue = np.delete(self.SHistoryPlateValue,-1,None)
        self.SUnit -= CONST_LiNewUnit
        return GetHowManyMoney
    #---------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------------------
def PreparateStockID(StockIndexList,HowManyStockYouWant):
    tmpPath = AllStockPath + 'AllStockList.csv'
    StockList_csv_data = pd.read_csv(tmpPath)
    #StockList_csv_data = pd.read_csv('/Users/desmond/Famliy/Liu/Final/ParamterTest/AllStockList.csv')
    for iline in range(HowManyStockYouWant):
    #for iline in range(len(StockList_csv_data)):
        StockIndexList.append(StockList_csv_data['code'][iline]) 
#---------------------------------------------------------------------------------------------------------------------------
def date_range(beginDate, endDate):
    dates = []
    dt = datetime.datetime.strptime(beginDate, "%Y-%m-%d")
    date = beginDate[:]
    while date <= endDate:
        dates.append(date)
        dt = dt + datetime.timedelta(1)
        date = dt.strftime("%Y-%m-%d")
    return dates 
#---------------------------------------------------------------------------------------------------------------------------
def TodayIsTradeDay(DateListIniday):
    #print("check trade day")
    # DateListIniday e.g.  2020-02-10
    # query_date e.g 20200210
    da = datetime.date(int(DateListIniday[0:4]), int(DateListIniday[5:7]), int(DateListIniday[8:11]))
    boll = is_workday(da)
    return boll
#---------------------------------------------------------------------------------------------------------------------------
def ReCSV(idayStr,StockIndexStr):
    #------------------------------------------------------
    # read csv data, by stock unique index and day
    # return pandas file!
    #------------------------------------------------------
    filepath = RawDataPath + idayStr + '/' + StockIndexStr + '.csv'
    if(os.path.isfile(filepath)):
        #print(filepath)
        csv_data = pd.read_csv(filepath)
        if(len(csv_data)!=CONST_DayStep):
            filepath = EmptyDataPath + 'empty.csv'
            csv_data = pd.read_csv(filepath)
        return csv_data
    else:
        filepath = EmptyDataPath + 'empty.csv'
        #print(filepath)
        csv_data = pd.read_csv(filepath)
        return csv_data 
#---------------------------------------------------------------------------------------------------------------------------
def RePlateCSV(idayStr,StockIndexStr):
    filepath = CompCodePath + idayStr + '/' + 'test_' + StockIndexStr + '.csv'
    #print("RePlateCSV ",filepath) 
    if(os.path.isfile(filepath)):
        #print("RePlateCSV ",filepath)
        csv_data = pd.read_csv(filepath)
        if(len(csv_data)!=CONST_DayStep):
            filepath = EmptyDataPath + 'empty.csv'
            csv_data = pd.read_csv(filepath)
        return csv_data
    else:
        filepath = EmptyDataPath + 'empty.csv'
        #print(filepath)
        #print("RePlateCSV ",filepath)
        csv_data = pd.read_csv(filepath)
        return csv_data 
#---------------------------------------------------------------------------------------------------------------------------
def EstUnit(price):
# estimate hands number 
# price >200 abandom before
    if(price>=180 and price<200):
        return 1
    else:
        return(math.floor(200./price)) 
def ReturnNewHandsInUnit(ASSET,StockClassList):
    return 0
def ChangeMoneyToCalHandsInUnit(iday,ASSET,OUTPUT):
    return 0
def ReturnActualUnit(PriceNow,PriceOld):
    TmpAmp = float(abs(PriceNow - PriceOld)/PriceOld)
    TmpActualUnit = int(math.floor(TmpAmp/OperatThres))
    #print("ReturnActualUnit",PriceNow,PriceOld,TmpAmp)
    return TmpActualUnit
#---------------------------------------------------------------------------------------------------------------------------
def ReadSCICSVFile(idayStr):
    filepath = SCIStockPath + idayStr + '/sh.000001.csv'
    #print(filepath)
    if(os.path.isfile(filepath)):
        return pd.read_csv(filepath)
    else:
        filepath = EmptyDataPath + 'empty.csv'
        return pd.read_csv(filepath)  
#---------------------------------------------------------------------------------------------------------------------------
def PlateDepTest(MyAccount,StockIndexList,iday,OUTPUT):
    #print("find_one ",iday,MyAccount.MyStockClass[ix].SCode)
    # for ix in range(20):
    #     if(MyAccount.MyStockClass[ix].isInPool==GoodIndex):
    #         print("find_one ",iday,MyAccount.MyStockClass[ix].SCode)
    # # 1. jugde plate index file path exist or not!
    #print("find_one ",iday,MyAccount.MyStockClass[1].isInPool,MyAccount.MyStockClass[1].SUnit,MyAccount.MyStockClass[1].SHandsInUnit)
    path = CompCodePath + MyAccount.MyOperaDateList[iday]
    if not os.path.exists(path):
        # only update 2 value
        #MyAccount.EndOfDay(iday)
        print("bad path day!")
        return 0
    GoodForTrade = 0
    # 1.1 tell My account, it is a new day!
    MyAccount.UpdateMyTodayIndex(iday)
    # 1.2 clear all stock today buy
    MyAccount.InitNewDay()

    OUTPUT[2] = MakeSCIRateList(MyAccount,iday)
    print("Today have in-pool stock count ",MyAccount.ReturnInPoolCount())
    # 2. set each step gold money(buy and sell)
#    MergeStep = 4       # which means every step is 10 min, if MergeStep = 3, it means 15min
    
    BuyProportion       = 0.2 
    TodayGoldBuyValue   = BuyProportion * MyAccount.ReturnMyAssetInLastDay() 
    SellProportion      = 0.    # 
    TodayGoldSellValue  = 0.
    
    JudgeProportion = 0.2
    if(MyAccount.IsBlanace==BadIndex):
        if(MyAccount.MyLastDayHoldValue/MyAccount.ReturnMyAssetInLastDay() > 1.- JudgeProportion):
            MyAccount.IsBlanace = GoodIndex
            print("change")
            SellProportion = 0.3
            TodayGoldSellValue = SellProportion * MyAccount.ReturnMyAssetInLastDay()
        else:
            SellProportion = 0.2
            TodayGoldSellValue = SellProportion * MyAccount.MyLastDayHoldValue
    else:
        SellProportion = 0.2
        TodayGoldSellValue = SellProportion * MyAccount.MyLastDayHoldValue
     
    print("Total gold ",iday,TodayGoldBuyValue,TodayGoldSellValue)
    TotalIntegralBuyMoney   = 0.
    TotalIntegralSellMoney  = 0.
    # 3. loop this day each time point!
    IntegralSellMoneyList = []
    IntegralBuyMoneyList = []
    GoalSellMoneyList = []
    GoalBuyMoneyList = []
    
    for step in range(int(CONST_DayStep/MergeStep)):
        #print("intmoney ",TotalIntegralBuyMoney," ",TotalIntegralSellMoney) 
        TmpThisStepBuyMoney = 0.
        TmpThisStepSellMoney = 0.
        istep = int(step * MergeStep)   # the real step, beacause data is 5min step
        ThisStepBuyMoney = 0            # need 
        ThisStepSellMoney = 0

        StandThisStepSellMoney  = 0. 
        if(TotalIntegralSellMoney < TodayGoldSellValue):
            StandThisStepSellMoney = (TodayGoldSellValue - TotalIntegralSellMoney)/(int(CONST_DayStep/MergeStep) - step) 
        
        StandThisStepBuyMoney   = 0.
        if(TotalIntegralBuyMoney < TodayGoldBuyValue): 
            StandThisStepBuyMoney = (TodayGoldBuyValue - TotalIntegralBuyMoney)/(int(CONST_DayStep/MergeStep) - step) 
        
        FuncS = 0.

        if(step<3):
            #print("case1")
            FuncS = 1.
        else:
            if(TotalIntegralSellMoney!=0 and TotalIntegralBuyMoney!=0):
                #print("case2")
                FuncS = TotalIntegralSellMoney/TotalIntegralBuyMoney
            else:
                #print("case3")
                FuncS = 1.
        #print("FuncS ",FuncS)     
        SingleSCIInfo = ReadSCICSVFile(MyAccount.MyOperaDateList[iday])
        ThisStepSCIIndex = SingleSCIInfo['open'][istep]
        ThisStepSCIRate = MyAccount.ReutrnLastSCIRate(ThisStepSCIIndex)
        ActualBuyMoney = StandThisStepBuyMoney * (1. + ThisStepSCIRate * 20.)*FuncS
        ActualSellMoney = StandThisStepSellMoney * (1. - ThisStepSCIRate * 40.)/FuncS
        #print("ActualBuyMoney ",ActualBuyMoney," ",StandThisStepBuyMoney," ",FuncS)
        #print("ActualSellMoney ",ActualSellMoney," ",StandThisStepSellMoney," ",FuncS)
        GoalSellMoneyList.append(ActualSellMoney)
        GoalBuyMoneyList.append(ActualBuyMoney)

        
        #print("TotalIntegral ",TotalIntegralBuyMoney,TotalIntegralSellMoney)

        #print("act ",ActualSellMoney,ActualBuyMoney)
        # Buy/Sell TableInLoop[0] -> relative rate(need plate index)
        # Buy/Sell TableInLoop[1] -> stock code
        # Buy/Sell TableInLoop[2] -> stock current price
        # Buy/Sell TableInLoop[3] -> absolut rate in price
        # Buy/Sell TableInLoop[4] -> plate value in price
        
        
        #---------------------------------------------------------------------------------------------------------------------------
        # 3.2 while sell money not reach gold money we want, continue to sell
        # same structure as buy part!
        #print("end buy")
        
        # old ActualSellMoney = EachStepSellValue * float(step+1)
        SellTableInLoop = [ ]
        ThisStepSellOp = 0
        if(MyAccount.ExcDay > 1):
            while(TmpThisStepSellMoney < ActualSellMoney):
                ThisStepSellOp += 1
                #print("sell this step gold money ",EachStepSellValue * float(step+1))
                # if Buy or Sell list empty, then, resort all 
                #print("begin cal sell table ",SellTableInLoop[0])
                if(SellTableInLoop == []):  
                    CalReRateInThisStep(MyAccount,StockIndexList,SellTableInLoop,iday,istep,SELLIndex)
                # if after calculate relative rate, still empty, go to next step
                if(SellTableInLoop != []):
                    # according able to sell hands, delete some list element.
                    SellTableInLoop = UpdateSellTable(MyAccount,SellTableInLoop)
                if(SellTableInLoop == []):
                    break
                #print("after cal sell table ",SellTableInLoop[0])
                WhichOneIsBuyOrSell = FindMaxOrMinInList(SellTableInLoop,SELLIndex)
                if(WhichOneIsBuyOrSell==FATAL_ERROR):
                    break
                ThisStepOutputList = copy.deepcopy(SellTableInLoop[WhichOneIsBuyOrSell])
                #print("sell ThisStepOutputList ",ThisStepOutputList)
                # sell!
                #print("sell re-rate ",istep," ",SellTableInLoop[0])
                # ThisStepOutputList[0] = ReRate(will change)
                # ThisStepOutputList[1] = PriceRate
                # ThisStepOutputList[2] = PriceRate+App(will change)
                # ThisStepOutputList[3] = SIndex
                # ThisStepOutputList[4] = PriceInLoop
                # ThisStepOutputList[5] = PlateValue
                # ThisStepOutputList[6] = TypeIndex
                TmpSellMoney = AfterFinalSortSell(MyAccount,ThisStepOutputList)
                #for SIndex in range(MyAccount.MyHowManyStock):
                #    if(MyAccount.MyStockClass[SIndex].SAbleToSellHands!=0):
                #        print("sell",istep,MyAccount.MyStockClass[SIndex].SCode,MyAccount.MyStockClass[SIndex].SUnit,len(MyAccount.MyStockClass[SIndex].SHistoryBuyPrice))
                MyAccount.MyCash += TmpSellMoney
                TotalIntegralSellMoney += TmpSellMoney
                TmpThisStepSellMoney += TmpSellMoney
                if(TmpThisStepSellMoney < ActualSellMoney):
                    #print("sell in while TotalIntegralBuyMoney ",TotalIntegralSellMoney)
                    ReUpdateFiveList(MyAccount,WhichOneIsBuyOrSell,SellTableInLoop,iday,istep,SELLIndex)
                else:
                    #print("sell this step finish money ",TotalIntegralSellMoney)
                    break
        IntegralSellMoneyList.append(TotalIntegralSellMoney)
        # 3.1 while the cost not reach gold money we want, continue to buy
        # in while loop, only buy or sell one stock once!
        # maybe you need some times loop to reach the gold!
        # old ActualBuyMoney = EachStepBuyValue * float(step+1)
        #print("end sell, begin buy!")
        #---------------------------------------------------------------------------------------------------------------------------
        BuyTableInLoop = [ ]
        ThisStepBuyOp = 0
        while(TmpThisStepBuyMoney < ActualBuyMoney):
            ThisStepBuyOp += 1
            #print("buy this step gold money ",EachStepBuyValue * float(step+1))
            # 3.1.1 if Buy list empty, then, resort all
            #print("begin cal buy table ",BuyTableInLoop[0])
            if(BuyTableInLoop == []):
                CalReRateInThisStep(MyAccount,StockIndexList,BuyTableInLoop,iday,istep,BUYIndex)
            # 3.1.1 still buy stock according the first stock in buy rate table.
            #print(istep, " ", len(BuyTableInLoop[0]),len(BuyTableInLoop[1]),len(BuyTableInLoop[2]))
            if(BuyTableInLoop == []):
                break
            WhichOneIsBuyOrSell = FindMaxOrMinInList(BuyTableInLoop,BUYIndex)
            ThisStepOutputList = copy.deepcopy(BuyTableInLoop[WhichOneIsBuyOrSell])
            #print("buy ThisStepOutputList ",ThisStepOutputList)
            TmpBuyMoney = AfterFinalSortBuy(MyAccount,ThisStepOutputList)
            if(TmpBuyMoney == -999):
                break 
            MyAccount.MyCash -= TmpBuyMoney
            TotalIntegralBuyMoney += TmpBuyMoney
            TmpThisStepBuyMoney += TmpBuyMoney
            #ReturnStatistics(MyAccount)
            ## 3.1.2 re-update buy rate table, check this
            if(TmpThisStepBuyMoney < ActualBuyMoney):
                #print("in while reupdate ",MyAccount.StockClassList[BuyTableInLoop[1][0]].SHistoryBuyPrice)
                #print("buy in while TotalIntegralBuyMoney ",TotalIntegralBuyMoney)
                ReUpdateFiveList(MyAccount,WhichOneIsBuyOrSell,BuyTableInLoop,iday,istep,BUYIndex)
            else:
                #print("buy this step finish money ",TotalIntegralBuyMoney)
                break
        IntegralBuyMoneyList.append(TotalIntegralBuyMoney)
        OUTPUT[3].append(ThisStepSellOp)
        OUTPUT[4].append(ThisStepBuyOp)       
 #---------------------------------------------------------------------------------------------------------------------------
    #print("MakeIntegralMoneyOutputFile ",len(IntegralSellMoneyList),len(IntegralBuyMoneyList))
    MakeIntegralMoneyOutputFile(IntegralSellMoneyList,IntegralBuyMoneyList,\
                                GoalSellMoneyList,GoalBuyMoneyList,MyAccount.MyOperaDateList[iday])
    # end of today time point loop!
    # 4.0 update info for next day
    # No.1  LastDayLastStepPrice
    # No.2  LastPlateValue
    # No.3  In or out pool
    # No.4  able to sell hands/ clear today buy hands
    MyAccount.EndOfDay(iday)
    # for SIndex in range(MyAccount.MyHowManyStock):
    #     if(MyAccount.MyStockClass[SIndex].SAbleToSellHands!=0):
    #         print(MyAccount.MyStockClass[SIndex].SCode,MyAccount.MyStockClass[SIndex].SUnit,len(MyAccount.MyStockClass[SIndex].SHistoryBuyPrice))
            #print(MyAccount.MyStockClass[SIndex].SCode,MyAccount.MyStockClass[SIndex].SUnit,MyAccount.MyStockClass[SIndex].SAbleToSellHands,MyAccount.MyStockClass[SIndex].SHandsInUnit)
    #print("End of day ",MyAccount.MyOperaDateList[iday])
    OUTPUT[0] = TotalIntegralBuyMoney
    OUTPUT[1] = TotalIntegralSellMoney

    print("End of day Cash ",MyAccount.MyOperaDateList[iday]," ",MyAccount.MyCash)
    print("End of day Hold value ",MyAccount.MyOperaDateList[iday]," ",MyAccount.MyLastDayHoldValue)
    print("End of day all money ",MyAccount.MyOperaDateList[iday]," ",MyAccount.ReturnMyAssetInLastDay())
    return 1

    # for SIndex in range(MyAccount.MyHowManyStock):
    #     #print("after one day")
    #     # if(MyAccount.MyStockClass[SIndex].SPlateIndex != 'None'):
    #     #     print("goodInit1 ",iday,MyAccount.MyStockClass[SIndex].SCode)
    #     #     print("goodInit2 ",iday,MyAccount.MyStockClass[SIndex].SPlateIndex)
    #     #     print("goodInit3 ",iday,MyAccount.MyStockClass[SIndex].SBase)
    #     #     print("goodInit4 ",iday,MyAccount.MyStockClass[SIndex].isInPool)
    #     if(MyAccount.MyStockClass[SIndex].isInPool == GoodIndex):
    #         print("goodInit1 ",iday,MyAccount.MyStockClass[SIndex].SCode)
    #         print("goodInit2 ",iday,MyAccount.MyStockClass[SIndex].SPlateIndex)
    #         print("goodInit2 ",iday,MyAccount.MyStockClass[SIndex].SBase)
    
#---------------------------------------------------------------------------------------------------------------------------                   
def PreparateStockIDInPlate(StockIndexList):
    # ComCodePath include a part of file name
    for PlateType in range(len(AllPlateIndexList)):
        CompCode = pd.read_csv(CompCodePath + 'ComponentStockCode_' + AllPlateIndexList[PlateType] +'.csv', converters={'code': lambda x: str(x)})
        for i in range(len(CompCode)):
            TmpStr = str(CompCode['code'][i])
            if(TmpStr[0:1]=='0' or TmpStr[0:1]=='3'):
                TmpStr = 'sz.' + TmpStr
            if(TmpStr[0:1]=='6'):
                TmpStr = 'sh.' + TmpStr
            StockIndexList.append(TmpStr)
            #StockIndexList.append(CompCode['code'][i])
def PlateInitMyAcc(MyAccount,iday):
    print("begin PlateInitMyAcc")
    SingleSCIInfo = ReadSCICSVFile(MyAccount.MyOperaDateList[iday])
    MyAccount.MyLastSCIIndex = SingleSCIInfo['end'][CONST_DayStep-1]
    print("length ",MyAccount.MyHowManyStock,len(MyAccount.MyStockClass))
    for SIndex in range(MyAccount.MyHowManyStock):
        if(MyAccount.MyStockClass[SIndex].SPlateIndex=='None'):
            continue
        #print("MyAccount.MyStockClass[SIndex].SPlateIndex ",MyAccount.MyStockClass[SIndex].SPlateIndex)
        # Must have this stock
        SingleStockInfo = ReCSV(MyAccount.MyOperaDateList[iday],MyAccount.MyStockClass[SIndex].SCode)
        if(len(SingleStockInfo)==0):
            continue
        TmpTodayLastPrice = SingleStockInfo['close'][CONST_DayStep-1]
        MyAccount.MyStockClass[SIndex].UpdateLastDayLastStepPrice(TmpTodayLastPrice)
        
        # Must have plate index and update it
        #print("MyAccount.MyStockClass[SIndex].SPlateIndex ",MyAccount.MyStockClass[SIndex].SPlateIndex)
        SinglePlateInfo = RePlateCSV(MyAccount.MyOperaDateList[iday],MyAccount.MyStockClass[SIndex].SPlateIndex)
        if(len(SinglePlateInfo) == 0):
            continue
        TmpTodayLastPlateIndex = SinglePlateInfo['end'][CONST_DayStep-1]
        #print("TmpTodayLastPlateIndex ",TmpTodayLastPlateIndex)
        # update all stock in big pool info
        MyAccount.MyStockClass[SIndex].UpdateLastPlateValue(TmpTodayLastPlateIndex)  
        MyAccount.MyStockClass[SIndex].SBase = GoodIndex
#---------------------------------------------------------------------------------------------------------------------------        
def CalReRateInThisStep(MyAccount,StockIndexList,TableInLoop,iday,istep,TypeIndex):
    #print("begin_CalReRateInThisStep",iday,TypeIndex)
    for SIndex in range(MyAccount.MyHowManyStock):
        # only have plate index and has base two price, call big pool
        if(MyAccount.MyStockClass[SIndex].SPlateIndex == 'None' \
            or MyAccount.MyStockClass[SIndex].SBase == BadIndex):
            continue
        #print("calrerate ",MyAccount.MyStockClass[SIndex].SCode)
        # only sell need enter big pool
        # if you want buy, just opearte in big pool
        if(TypeIndex==SELLIndex):
            if(MyAccount.MyStockClass[SIndex].isInPool == BadIndex):
                continue
            if(MyAccount.MyStockClass[SIndex].SAbleToSellHands == 0):
                continue
        # get this stock info .csv
        SingleStockInfo = ReCSV(MyAccount.MyOperaDateList[iday],str(StockIndexList[SIndex]))
        if(len(SingleStockInfo)==0):
            continue
        PriceInLoop = SingleStockInfo['open'][istep]    # get current price
        #print(iday," ",istep," ",MyAccount.MyStockClass[SIndex].SCode," ",PriceInLoop)
        # get relavent plate index file
        # which need read plate index file!!!!!
        SinglePlateInfo = RePlateCSV(MyAccount.MyOperaDateList[iday],MyAccount.MyStockClass[SIndex].SPlateIndex)
        if(len(SinglePlateInfo)==0):
            continue
        TmpPlateValue = SinglePlateInfo['open'][istep]  # get current plate value
        TmpReRate = 0. 
        if(TypeIndex==BUYIndex):
            TmpReRate = MyAccount.MyStockClass[SIndex].ReturnRelativeRate(PriceInLoop,TmpPlateValue,BUYIndex)
            PriceRate = MyAccount.MyStockClass[SIndex].ReturnLastSPRate(PriceInLoop)
            TmpApp = ReturnAppValueInTable(MyAccount.MyStockClass[SIndex].SUnit,BUYIndex)
        elif(TypeIndex==SELLIndex):
            TmpReRate = MyAccount.MyStockClass[SIndex].ReturnRelativeRate(PriceInLoop,TmpPlateValue,SELLIndex)
            PriceRate = MyAccount.MyStockClass[SIndex].ReturnLastSPRate(PriceInLoop)
            TmpApp = ReturnAppValueInTable(MyAccount.MyStockClass[SIndex].SUnit,SELLIndex)
        #print("calrerate ",MyAccount.MyStockClass[SIndex].SCode," ",TmpReRate)
        #if(TypeIndex==SELLIndex):
            #print("sell be up ",iday,istep,TmpReRate)
        TmpInfoList = [TmpReRate,PriceRate,PriceRate+TmpApp,SIndex,PriceInLoop,TmpPlateValue,TypeIndex]
        #UpdateFiveList(TableInLoop,TmpReRate,PriceRate,SIndex,PriceInLoop,TmpPlateValue,TypeIndex)
        UpdateFiveList(TableInLoop,TmpInfoList,TypeIndex)
        #print(istep, " in_CalReRateInThisStep ", len(TableInLoop[0]),len(TableInLoop[1]),len(TableInLoop[2]))
    # if(TypeIndex==SELLIndex):
    #     print("in cal",TableInLoop[0])
#---------------------------------------------------------------------------------------------------------------------------      
# WDF_last: isInPool should be check
# buy/sell money should update cash!
def AfterSortBuy(MyAccount,LastFiveMinSIndex,LastFiveMinSIndexPrice,LastFiveMinPlateValue):
    # get scode and price 
    SIndex = LastFiveMinSIndex[0]
    PriceInLoop = LastFiveMinSIndexPrice[0]
    PlateValue = LastFiveMinPlateValue[0]
    # get price and unit, however it has two case:
    # No.1 have history buy;
    # No.2 not have history buy
    PriceOld = 0.
    if(MyAccount.MyStockClass[SIndex].SHistoryBuyPrice != []):
        PriceOld = MyAccount.MyStockClass[SIndex].SHistoryBuyPrice[-1]
    else:
        PriceOld = MyAccount.MyStockClass[SIndex].SLastDayLastStepPrice
    # always be 1 unit to opearate 
    # the first time buy in all loop day, 
    # init it, only once, no need change!
    if(MyAccount.MyStockClass[SIndex].isInit == BadIndex):
        MyAccount.MyStockClass[SIndex].isInit = GoodIndex
        MyAccount.MyStockClass[SIndex].UpdateHandsInUnit(EstUnit(PriceInLoop))
    TmpCostMoney = MyAccount.MyStockClass[SIndex].GenearalNewLiBuyStock(PriceInLoop,PlateValue)
    if(TmpCostMoney > MyAccount.MyCash):
        TmpCostMoney = -999
    return TmpCostMoney
#---------------------------------------------------------------------------------------------------------------------------
def AfterFinalSortBuy(MyAccount,ThisStepOutputList):
    SIndex = ThisStepOutputList[3]
    PriceInLoop = ThisStepOutputList[4]
    PlateValue = ThisStepOutputList[5]
    PriceOld = 0.
    if(MyAccount.MyStockClass[SIndex].SHistoryBuyPrice != []):
        PriceOld = MyAccount.MyStockClass[SIndex].SHistoryBuyPrice[-1]
    else:
        PriceOld = MyAccount.MyStockClass[SIndex].SLastDayLastStepPrice
    # only set hands in unit once!
    # wdf_last
    if(MyAccount.MyStockClass[SIndex].SHandsInUnit == 0):
        MyAccount.MyStockClass[SIndex].UpdateHandsInUnit(EstUnit(PriceInLoop))
    TmpCostMoney = MyAccount.MyStockClass[SIndex].GenearalNewLiBuyStock(PriceInLoop,PlateValue)
    if(TmpCostMoney > MyAccount.MyCash):
        TmpCostMoney = -999
    return TmpCostMoney
#---------------------------------------------------------------------------------------------------------------------------
def AfterSortSell(MyAccount,TopFiveMaxSIndex,TopFiveMaxSIndexPrice):
    SIndex = TopFiveMaxSIndex[0]
    PriceInLoop = TopFiveMaxSIndexPrice[0]
    TmpGetMoney = MyAccount.MyStockClass[SIndex].GenearalNewLiSellStock(PriceInLoop)
    return TmpGetMoney
#---------------------------------------------------------------------------------------------------------------------------
def AfterFinalSortSell(MyAccount,ThisStepOutputList):
    SIndex = ThisStepOutputList[3]
    PriceInLoop = ThisStepOutputList[4]
    TmpGetMoney = MyAccount.MyStockClass[SIndex].GenearalNewLiSellStock(PriceInLoop)
    #print("AfterFinalSortSell ",SIndex,PriceInLoop,TmpGetMoney)
    return TmpGetMoney
#---------------------------------------------------------------------------------------------------------------------------
def FindMaxOrMinInList(TableInLoop,BuyOrSell):
    # stock index
    WhichOneIsBuyOrSell = 0
    TmpPriceRateAndApp = TableInLoop[0][2]
    if(BuyOrSell == SELLIndex):
        # find
        TmpReRateMax = TableInLoop[0][0]
        #outputList = TableInLoop[0]
        for ir in range(len(TableInLoop)):
            if(TmpReRateMax - CONST_FinalScreenSELLCut <= TableInLoop[ir][0]):
                if(TableInLoop[ir][2] > TmpPriceRateAndApp):
                    #outputList = TableInLoop[ir]
                    WhichOneIsBuyOrSell = ir
                    break
                else:
                    continue
            else:
                break    
    if(BuyOrSell == BUYIndex):
        TmpReRateMin = TableInLoop[0][0]
        #outputList = TableInLoop[0]
        for ir in range(len(TableInLoop)):
            if(TableInLoop[ir][0] <= TmpReRateMin + CONST_FinalScreenBUYCut):
                if(TableInLoop[ir][2] < TmpPriceRateAndApp):
                    #outputList = TableInLoop[ir]
                    WhichOneIsBuyOrSell = ir
                    break
                else:
                    continue
            else:
                break   
    #outputList = 
    #outputList = TableInLoop[WhichOneIsBuyOrSell].copy()
    return WhichOneIsBuyOrSell

#---------------------------------------------------------------------------------------------------------------------------         
#def UpdateFiveList(TableInLoop,ReRate,PriceRate,SIndex,CurrentPrice,PlateValue,BuyOrSell):
def UpdateFiveList(TableInLoop,InfoList,BuyOrSell):
    # SELL order: from large to small!
    # BUY order: from small to big
    # keep mind
    TmpPos = 999
    ReRate = InfoList[0]
    if(TableInLoop != []):
        if(BuyOrSell == SELLIndex):
            for i in range(len(TableInLoop)):
                if(ReRate > TableInLoop[i][0]):
                    TmpPos = i
                    break
        if(BuyOrSell == BUYIndex):
            for i in range(len(TableInLoop)):
                if(ReRate < TableInLoop[i][0]):
                    TmpPos = i
                    break
    else:
        TmpPos = 0
    #---------------------------------------------------------------------------------------------------------------------------
    if(TmpPos == 999):
        TableInLoop.append(InfoList)
    else:
        TableInLoop.insert(TmpPos,InfoList)

#---------------------------------------------------------------------------------------------------------------------------
def ReUpdateFiveList(MyAccount,WhichOneIsBuyOrSell,TableInLoop,iday,istep,TypeIndex):
    # buy or sell use this same function to re-update relative rate list
    # only difference with type
    SIndex = TableInLoop[WhichOneIsBuyOrSell][3]
    PriceRate = TableInLoop[WhichOneIsBuyOrSell][1]
    TmpApp = ReturnAppValueInTable(MyAccount.MyStockClass[SIndex].SUnit,TypeIndex)
    PriceRateAndApp = PriceRate + TmpApp
    #---------------------------------------------------
    TmpPlateValue = TableInLoop[WhichOneIsBuyOrSell][5]
    TmpPlateRate = MyAccount.MyStockClass[SIndex].ReturnLastPIRate(TmpPlateValue)
    ReRate = PriceRateAndApp - TmpPlateRate
    
    TmpNewInsertList = TableInLoop[WhichOneIsBuyOrSell].copy()
    TmpNewInsertList[0] = ReRate
    TmpNewInsertList[2] = PriceRateAndApp

    # TmpNewInsertList = [ReRate,PriceRate,PriceRateAndApp,SIndex,]
    # check the first rate with the other four rate!
    # case1: if still larger than the other four, should be at second place, then delete the first in list.
    # case2: if smaller than the other four, not insert, just delete the first.
    # case3: if not case1 & 2, insert list, delete the first. 
    WhichPlaceInsert = 999
    if(len(TableInLoop) != 0):
        for ir in range(len(TableInLoop)):
            if(TypeIndex == SELLIndex):
                if(ReRate > TableInLoop[ir][0]):
                    WhichPlaceInsert = ir
                    break
            if(TypeIndex == BUYIndex):
                if(ReRate < TableInLoop[ir][0]): 
                    WhichPlaceInsert = ir
                    break    
    # always do it, according insert place, you need delete WhichOneIsBuyOrSell 
    #print("ReUpdateFiveList ",len(TableInLoop[0]),WhichPlaceInsert,WhichOneIsBuyOrSell)
    # small than each one in SELL list
    # larger than each one in BUY list
    # just delete old one!
    if(WhichPlaceInsert==999):
        #print("WhichPlaceInsert ",WhichPlaceInsert)
        del(TableInLoop[WhichOneIsBuyOrSell])
        TableInLoop.append(TmpNewInsertList)
    else:  
        #print("go_on")
        TableInLoop.insert(WhichPlaceInsert,TmpNewInsertList)
        if(WhichPlaceInsert <= WhichOneIsBuyOrSell):
            WhichOneIsBuyOrSell += 1
        del(TableInLoop[WhichOneIsBuyOrSell])
#---------------------------------------------------------------------------------------------------------------------------
def UpdateSellTable(MyAccount,SellTableInLoop):
    newTable = []
    for ir in range(len(SellTableInLoop)):
        TmpSIndex = SellTableInLoop[ir][3]
        if(MyAccount.MyStockClass[TmpSIndex].SAbleToSellHands!=0):
            newTable.append(SellTableInLoop[ir])
    return newTable

#---------------------------------------------------------------------------------------------------------------------------
def ReturnAppValueInTable(CurrentUnit,BuyOrSell):
    TmpAppValue = 0
    # buy type  -> 0
    # sell type -> 1
    # if(BuyOrSell==BUYIndex):
    #     if(CurrentUnit==0):
    #         TmpAppValue = -1.
    #     elif(CurrentUnit==1):
    #         TmpAppValue = -0.5
    #     elif(CurrentUnit==2):
    #         TmpAppValue = 0.
    #     elif(CurrentUnit==3):
    #         TmpAppValue = 2.
    #     elif(CurrentUnit==4):
    #         TmpAppValue = 4.
    #     elif(CurrentUnit==5):
    #         TmpAppValue = 6.
    #     elif(CurrentUnit>=6):
    #         TmpAppValue = 6.
    # if(BuyOrSell==SELLIndex):
    #     if(CurrentUnit==0):
    #         TmpAppValue = -1.
    #     elif(CurrentUnit==1):
    #         TmpAppValue = -0.5
    #     elif(CurrentUnit==2):
    #         TmpAppValue = 0.
    #     elif(CurrentUnit==3):
    #         TmpAppValue = 2.
    #     elif(CurrentUnit==4):
    #         TmpAppValue = 4.
    #     elif(CurrentUnit==5):
    #         TmpAppValue = 6.
    #     elif(CurrentUnit>=6):
    #         TmpAppValue = 6.
    
    if(BuyOrSell==BUYIndex):
        if(CurrentUnit==0):
            TmpAppValue = -3.
        elif(CurrentUnit==1):
            TmpAppValue = -2.
        elif(CurrentUnit==2):
            TmpAppValue = -1.
        elif(CurrentUnit==3):
            TmpAppValue = 0.
        elif(CurrentUnit==4):
            TmpAppValue = 2.
        elif(CurrentUnit==5):
            TmpAppValue = 4.
        elif(CurrentUnit>=6):
            TmpAppValue = 6.
    if(BuyOrSell==SELLIndex):
        if(CurrentUnit==0):
            TmpAppValue = -3.
        elif(CurrentUnit==1):
            TmpAppValue = -2.
        elif(CurrentUnit==2):
            TmpAppValue = -1.
        elif(CurrentUnit==3):
            TmpAppValue = 0.
        elif(CurrentUnit==4):
            TmpAppValue = 1.
        elif(CurrentUnit==5):
            TmpAppValue = 2.
        elif(CurrentUnit>=6):
            TmpAppValue = 3.
    
    return TmpAppValue/100.
def ReturnStatistics(MyAccount):
    StatRe = [0,0,0,0,0,0]
    for SIndex in range(MyAccount.MyHowManyStock):
        if(MyAccount.MyStockClass[SIndex].SUnit==1):
            StatRe[0] += 1
        elif(MyAccount.MyStockClass[SIndex].SUnit==2):
            #print("find_one ",MyAccount.MyStockClass[SIndex].SCode)
            StatRe[1] += 1    
        elif(MyAccount.MyStockClass[SIndex].SUnit==3):
            StatRe[2] += 1 
        elif(MyAccount.MyStockClass[SIndex].SUnit==4):
            StatRe[3] += 1 
        elif(MyAccount.MyStockClass[SIndex].SUnit==5):
            StatRe[4] += 1 
        elif(MyAccount.MyStockClass[SIndex].SUnit>=6):
            StatRe[5] += 1 
    print("Unit Statistics ",StatRe)
    return 


def ReturnLastPIAlone(idayStr,WhichPlateIndex):
    if(WhichPlateIndex!=len(AllPlateIndexList)):
        SinglePlateInfo = RePlateCSV(idayStr,AllPlateIndexList[WhichPlateIndex])
    else:
        SinglePlateInfo = ReadSCICSVFile(idayStr)
    TmpTodayLastPlateIndex = SinglePlateInfo['end'][CONST_DayStep-1]
    return TmpTodayLastPlateIndex

def ReadSCICSVFile(idayStr):
    filepath = SCIStockPath + idayStr + '/sh.000001.csv'
    #print(filepath)
    if(os.path.isfile(filepath)):
        return pd.read_csv(filepath)
    else:
        filepath = EmptyDataPath + 'empty.csv'
        return pd.read_csv(filepath) 

def ReadAllCSV(idayStr,WhichPlateIndex):
    filepath = AllCSVPath + idayStr + '/all_' + str(AllPlateIndexList[WhichPlateIndex]) + '.csv'  
    print(filepath)
    if(os.path.isfile(filepath)):
        #print("RePlateCSV ",filepath)
        csv_data = pd.read_csv(filepath)
        return csv_data
    else:
        filepath = EmptyDataPath + 'empty.csv'
        #print(filepath)
        #print("RePlateCSV ",filepath)
        csv_data = pd.read_csv(filepath)
        return csv_data  

def ReturnLastPIInAll(idayStr,WhichPlateIndex):
    TmpTodayLastPlateIndex = 0.
    if(WhichPlateIndex!=len(AllPlateIndexList)):
        SinglePlateInfo = ReadAllCSV(idayStr,WhichPlateIndex)
        TmpTodayLastPlateIndex = SinglePlateInfo['end'][0]
    else:
        SinglePlateInfo = ReadSCICSVFile(idayStr)
        TmpTodayLastPlateIndex = SinglePlateInfo['end'][CONST_DayStep-1]
    return TmpTodayLastPlateIndex


def MakeSCIRateList(MyAccount,iday):

    TmpList = []

    SingleSCIInfo = ReadSCICSVFile(MyAccount.MyOperaDateList[iday])
    for istep in range(CONST_DayStep):
        ThisStepSCIIndex = SingleSCIInfo['open'][istep]
        ThisStepSCIRate = MyAccount.ReutrnLastSCIRate(ThisStepSCIIndex)
        TmpList.append(ThisStepSCIRate)

    return TmpList

def MakeOpOutputFile(OpList,idayStr,BuyOrSell):
    path = SourcePath + '/SCIRateRe'
    filepath = ''
    if(BuyOrSell==BUYIndex):
        filepath = path + '/' + 'buyop.csv'
    else:
        filepath = path + '/' + 'sellop.csv'
    if not os.path.exists(path):
           os.mkdir(path)
    if(os.path.isfile(filepath)):
        out = open(filepath, 'a')
        csv_writer = csv.writer(out)
        OpList.insert(0,idayStr)
        csv_writer.writerow(OpList)
        out.close()
    else:
        out = open(filepath, 'w')
        csv_writer = csv.writer(out)
        headList = ["date"]
        for istep in range(int(CONST_DayStep/MergeStep)):
            tmpstr = "a" + str(istep) 
            headList.append(tmpstr)
        csv_writer.writerow(headList)
        #csv_writer.writerow('\n')
        OpList.insert(0,idayStr)
        csv_writer.writerow(OpList)
        #csv_writer.writerow('\n')
        out.close()
def MakeSCIOutputFile(SCIList,idayStr):
    path = SourcePath + '/SCIRateRe' 
	#path = "/Users/desmond/Famliy/Liu/Final/ParamterTest/HJJclass/Li2/SCIRateRe/" 
    filepath = path + '/' + 'SCIToday.csv'
    if not os.path.exists(path):
           os.mkdir(path)
    if(os.path.isfile(filepath)):
        out = open(filepath, 'a')
        csv_writer = csv.writer(out)
        # out.write("date,a1,a2,a3,a4,a5,a6,a7,a8,a9,\
        #             a10,a11,a12,a13,a14,a15,a16,a17,a18,a19,\
        #             a20,a21,a22,a23,a24,a25,a26,a27,a28,a29,\
        #             a30,a31,a32,a33,a34,a35,a36,a37,a38,a39,\
        #             a40,a41,a42,a43,a44,a45,a46,a47,a48")
        SCIList.insert(0,idayStr)
        csv_writer.writerow(SCIList)
        #csv_writer.writerow('\n')
        out.close()
    else:
        out = open(filepath, 'w')
        csv_writer = csv.writer(out)
        #headList = []
        headList = ["date"]
        for istep in range(CONST_DayStep):
            tmpstr = "a" + str(istep) 
            headList.append(tmpstr)
        csv_writer.writerow(headList)
        #csv_writer.writerow('\n')
        SCIList.insert(0,idayStr)
        csv_writer.writerow(SCIList)
        #csv_writer.writerow('\n')
        out.close()

def MakeIntegralMoneyOutputFile(SellMoneyList,BuyMoneyList,SellGold,BuyGold,idayStr):
    path = SourcePath + '/SCIRateRe' 
    filepath = path + '/' + 'IntegralMoney.csv'
    if not os.path.exists(path):
           os.mkdir(path)
    if(os.path.isfile(filepath)):
        out = open(filepath, 'a')
        csv_writer = csv.writer(out)
        for istep in range(len(SellMoneyList)):
            tmpList = [idayStr,SellMoneyList[istep],SellGold[istep],BuyMoneyList[istep],BuyGold[istep]]
            csv_writer.writerow(tmpList)
        out.close()
    else:
        out = open(filepath, 'w')
        csv_writer = csv.writer(out)
        headList = ["date","sell","gold_sell","buy","gold_buy"]
        csv_writer.writerow(headList)
        for istep in range(len(SellMoneyList)):
            tmpList = [idayStr,SellMoneyList[istep],SellGold[istep],BuyMoneyList[istep],BuyGold[istep]]
            csv_writer.writerow(tmpList)
        out.close()





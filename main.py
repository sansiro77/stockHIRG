# 8.18 buy or sell according to plate index!

import pandas as pd
import time
import datetime
import requests

import os
from myClass import *




#HowManyStockYouWant = 100
StockIndexList = []     
#PreparateStockID(StockIndexList,HowManyStockYouWant)

PreparateStockIDInPlate(StockIndexList)

print("big pool ",len(StockIndexList))


# plate index test date!
#StartDate = '2017-02-17'
#EndDate = '2017-02-20'
#StartDate = '2018-03-01'
#EndDate = '2018-03-05'

StartDate = '2017-03-10' # atleast 2017 ok
#StartDate = '2017-03-10'
EndDate = '2021-09-27'
#EndDate = '2017-03-16'

DateList = date_range(StartDate,EndDate)
StockCount = len(StockIndexList)

TestDay = len(DateList)

SCIStockClass = SCIClass()
MyAcc = MyAccount(StockIndexList,DateList)

#print("my ",MyAcc.MyStockClass[-1].SPlateIndex,MyAcc.MyStockClass[0].SPlateIndex)
# for SIndex in range(MyAcc.MyHowManyStock):
#     if(MyAcc.MyStockClass[SIndex].SCode=='sz.000576'):
#         print("000576 ",SIndex)

savestr = 'good.csv'
out_sevenline = open(savestr, 'w')
out_sevenline.write("date,cash,hold,asset")
out_sevenline.write('\n')


path = SourcePath + '/SCIRateRe'
filepath = path + '/' + 'SCIToday.csv'
if(os.path.isfile(filepath)):
    os.remove(filepath) 
filepath = path + '/buyop.csv'
if(os.path.isfile(filepath)):
    os.remove(filepath)
filepath = path + '/sellop.csv'
if(os.path.isfile(filepath)):
    os.remove(filepath)
filepath = path + '/' + 'IntegralMoney.csv'
if(os.path.isfile(filepath)):
    os.remove(filepath) 

TmpBaddayCount = 0
tradedayCount = 0
OldPlateIndex = 0.
AllMoney = 50000.
WhichPlateIndex = 6
for iday in range(TestDay):
    print("begin iday ",DateList[iday])
    if(iday==0):
        PlateInitMyAcc(MyAcc,iday)
        MyAcc.ExcDay += 1
        #OldPlateIndex = ReturnLastPIAlone(DateList[iday],WhichPlateIndex)
        continue
    if(TodayIsTradeDay(MyAcc.MyOperaDateList[iday])==0):
        print("not working day!")
        continue
    tradedayCount += 1
    OUTPUT = [0., 0., [], [], []]
    #path = CompCodePath + MyAcc.MyOperaDateList[iday]
    # if not os.path.exists(path):
    #     TmpBaddayCount += 1
    #     continue
    # print("old ",ReturnLastPIAlone(DateList[iday],WhichPlateIndex))
    # AllMoney *= ReturnLastPIAlone(DateList[iday],WhichPlateIndex)/OldPlateIndex
    # print("wdf ",AllMoney," ",ReturnLastPIAlone(DateList[iday],WhichPlateIndex)/OldPlateIndex - 1.)
    # OldPlateIndex = ReturnLastPIAlone(DateList[iday],WhichPlateIndex)
    if(PlateDepTest(MyAcc,StockIndexList,iday,OUTPUT)):
        MyAcc.ExcDay += 1
        out_sevenline.write(DateList[iday]+ ',' + str(MyAcc.MyCash) + ',' + str(MyAcc.MyLastDayHoldValue) + ',' + str(MyAcc.ReturnMyAssetInLastDay()))
        out_sevenline.write('\n')
        print("in big loop ",MyAcc.MyCash," ",MyAcc.MyLastDayHoldValue," ",MyAcc.ReturnMyAssetInLastDay())
        print("buy cost ",OUTPUT[0])
        print("sell get ",OUTPUT[1])
        #print("sci ",OUTPUT[2])
        MakeSCIOutputFile(OUTPUT[2],MyAcc.MyOperaDateList[iday])
        ReturnStatistics(MyAcc)
        MakeOpOutputFile(OUTPUT[3],MyAcc.MyOperaDateList[iday],SELLIndex)
        MakeOpOutputFile(OUTPUT[4],MyAcc.MyOperaDateList[iday],BUYIndex)
        print("116_1",OUTPUT[3])
        print("116_2",OUTPUT[4])
    else:
        print("bad plate path! ",MyAcc.MyOperaDateList[iday])
print(TmpBaddayCount," in ",tradedayCount)

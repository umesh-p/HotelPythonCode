from flask import Flask
from flask_cors import CORS, cross_origin
from flask import request
from flask import jsonify

import pandas as pd
import numpy as np
import json
from pandas.io.json import json_normalize
from datetime import datetime
import requests
import sqlite3
import copy

import os

app = Flask(__name__)
CORS(app)

'''  Importing data for application'''

conn = sqlite3.connect('HotelAnalytics.db', timeout=10)
c = conn.cursor()

#========================================================================================================    
#Database Query functions 

def selectData(tableName):
    
    cursor = conn.execute('SELECT * from {}'.format(tableName))
    dataRows = cursor.fetchall();
    columns = [d[0] for d in cursor.description]
    data = [dict(zip(columns, row)) for row in dataRows]
    return data;
    

def insertData(tableName, columnNames , Values ):
    
     query = "INSERT into "+tableName+" "+str(columnNames)+" values "+str(Values);
     cursor = conn.execute(query)
     conn.commit()  
     return cursor.lastrowid;    
     
def updateData(tableName, columnNames, Values):
    
    setStatement = "";
    for i , j in zip(columnNames[1:],Values[1:]):
        if(type(j) is str):
            setStatement = setStatement + ('='.join((str(i),'"'+j+'"'))) +", ";    
        else:
            setStatement = setStatement + ('='.join((str(i),str(j)))) + ", ";
    query = "UPDATE "+str(tableName)+" SET "+setStatement.rstrip(', ')+" where id="+str(Values[0]);    
    print(query)
    conn.execute(query)    
    conn.commit()  
    return 'success'

def deleteData(tableName, param ,id):
    
    query = "DELETE from "+str(tableName)+" where "+param+" = "+str(id);
    conn.execute(query)    
    conn.commit()  
    return 'success'
   

#========================================================================================================    
   
@app.route('/login', methods=['GET', 'POST'])
def login():
    loginResponse = json.loads(request.data)
    if request.method == 'POST':
        userData = c.execute('select name,tablecount from loginData where name = ? and password = ? ' , (loginResponse['username'] ,loginResponse['password'])).fetchall();
        print(userData)
        if(len(userData) > 0):
            return jsonify({'success':True , 
                            'data':{ 
                                    'userName' : userData[0][0] , 
                                    'tableCount':userData[0][1]
                                    }, 
                            'message':'valid user'}) 
        else:
            return jsonify({'success':False ,'data':'' ,'message':'Invalid Username or Password'})   
    
    
@app.route('/inventory', methods=['GET', 'POST' , 'PUT' , 'DELETE'])
def inventory():
    
    userName = request.headers['userName']
    table = userName+'Stocks'

    if request.method == 'GET':
        data =  selectData(table)         
        return jsonify({'success':True , 'data':data })    
    
    if request.method == 'POST':
        response = dict(json.loads(request.data))
        allKeys  = tuple(response.keys())       
        allData = tuple(response.values())
        data = insertData(table ,allKeys, allData) 
        return jsonify({'success':True , 'data' : data })
            
    if request.method == 'PUT':
        response = dict(json.loads(request.data))
        allKeys  = tuple(response.keys())       
        allData = tuple(response.values())
        data = updateData(table ,allKeys, allData) 
        return jsonify({'success':True , 'data' : data })
    
    if request.method == 'DELETE':
        recordId = request.headers['recordId'];
        deleteData(table,'id',recordId)
        return jsonify({'success':True , 'data' : 'success' })
    
@app.route('/menu', methods=['GET', 'POST' , 'PUT' , 'DELETE'])
def menu():
    
    userName = request.headers['userName']
    table = userName+'Menu'
    materialTable = userName+'MenuMaterial'

    if request.method == 'GET':
        data =  selectData(table)
        materialData = selectData(materialTable)
        index = 0;
        if len(data) > 0:
            for menuItem in data:    
                material = [ item for item in materialData if (item['menuitemid'] == menuItem['id']) ]
                matDel = copy.deepcopy(material)
                
                for d in matDel:
                    del d['id'];
                    del d['menuitemid']
                    print(d)
                data[index]['materialUsed'] = matDel;
                index = index + 1
            
            return jsonify({'success':True , 'data':data })    
        return jsonify({'success':True , 'data':[] })  
    
    if request.method == 'POST':
        response = dict(json.loads(request.data))
        materials = response['materialUsed']
        del response['materialUsed']
        
        allKeys  = tuple(response.keys())[1:]       
        allData = tuple(response.values())[1:]
        data = insertData(table ,allKeys, allData)
        
        keys = list(materials[0].keys()) 
        keys.append('menuitemid')

        allvalues = "";
        for item in materials:
            values = list(item.values())
            values.append(data)
            allvalues = allvalues +","+str(tuple(values))

        insertData(materialTable ,tuple(keys), allvalues.strip(',')) 
        return jsonify({'success':True , 'data' : data })
            
    if request.method == 'PUT':
        
        response = dict(json.loads(request.data))
        materials = response['materialUsed']
        del response['materialUsed']
        
        allKeys  = tuple(response.keys()) 
        allData = tuple(response.values())
        data = updateData(table ,allKeys, allData) 
        keys = list(materials[0].keys()) 
        keys.append('menuitemid')
        deleteData(materialTable,'menuitemid',response['id'])

        newValues = "";
        for item in materials:
            values = list(item.values())
            values.append(response['id'])
            newValues = newValues +","+str(tuple(values))

        insertData(materialTable ,tuple(keys), newValues.strip(','))
        return jsonify({'success':True , 'data' : "success" })
    
    if request.method == 'DELETE':
        recordId = request.headers['recordId'];
        deleteData(table,'id',recordId)
        deleteData(materialTable,'menuitemid',recordId)

        return jsonify({'success':True , 'data' : 'success' })
    
@app.route('/saveOrder', methods=['GET', 'POST'])
def submitOrder():
    if request.method == 'POST':
        orderData = json.loads(request.data);        
        allOrderData = pd.read_csv(orderData["filename"]+"_orders.csv")
        newOrderNumber = allOrderData.tail(1)['ordernumber'] + 1;    
        newOrder = json_normalize(orderData ,'orderedItems' , ['date', 'filename' , 
                                                           'isWeekend' , 'tableIndex', 
                                                           'totalAmount' , 'orderHour'] );
        if(len(newOrderNumber) > 0 ):    
            newOrder['ordernumber'] = int(newOrderNumber);  
        else:
            newOrder['ordernumber'] = 1;
            
        newOrder = newOrder[['ordernumber', 'date', 'orderHour', 'isWeekend', 'tableIndex' ,'totalAmount','name','quantity','price']]                
        with open(orderData['filename']+"_orders.csv", 'a') as f:
             (newOrder).to_csv(f, header=False , index = False)
        return jsonify({'success':True})
    else:
        return jsonify({'success':False})

@app.route('/getOrderAnalysis', methods=['GET', 'POST'])
def getOrderAnalysis():
    if request.method == 'POST':
        
        orderData = json.loads(request.data);
        allOrderData = pd.read_csv(orderData['filename']+"_orders.csv")
        totalOrders = allOrderData.iloc[-1]['ordernumber'];    
        totalMoneyEarned = allOrderData['price'].sum();
        date_format = "%m/%d/%Y"
        a = datetime.strptime(allOrderData.iloc[0]['date'], date_format)
        b = datetime.strptime(allOrderData.iloc[-1]['date'], date_format)
        totalDays = b - a
        totalDays = int(totalDays.days) + 1;
                
        avgOrderPerDay = totalOrders / totalDays;
        avgEarningPerDay= totalMoneyEarned / totalDays;
        
        allItemNames =  list(allOrderData.iloc[:]['name'].unique());
        totalQuantityEach = []
        for item in allItemNames:
            totalQuantityEach.append(allOrderData.loc[allOrderData['name'] == item]['quantity'].sum())
            
        ordersOnWeekend = len(allOrderData.loc[allOrderData['isWeekend'] == True]['ordernumber'].unique())
        ordersOnWeekday = len(allOrderData.loc[allOrderData['isWeekend'] == False]['ordernumber'].unique())
                
        data = dict();
        
        lastSevenDays = list(allOrderData.iloc[:]['date'].unique()[-7:]);
        lastSevenDaysOrders = []
        
        for date in lastSevenDays:
            lastSevenDaysOrders.append(len(allOrderData.loc[allOrderData['date'] == date]['ordernumber'].unique()))
                    
          
            
        data['totalOrders'] = str(totalOrders);
        data['totalSale'] = str(totalMoneyEarned);
        data['avgOrderPerDay'] = str(avgOrderPerDay);
        data['avgEarningPerDay'] = str(avgEarningPerDay);
        data['allItemNames'] = [str(i) for i in allItemNames] ;
        data['totalQuantityEach'] = [str(i) for i in totalQuantityEach] ;
        data['ordersWeekend'] = str(ordersOnWeekend);
        data['ordersWeekday'] = str(ordersOnWeekday);            
        data['lastSevenDays'] = [str(i) for i in list(lastSevenDays)] ;
        data['lastSevenDaysOrders'] = [str(i) for i in list(lastSevenDaysOrders)] ;
         
        return jsonify({'success':True, 'data':json.dumps(data) })
    else:
        return jsonify({'success':False})




@app.route('/getAnalysis', methods=['GET', 'POST'])
def getAnalysis():
    if request.method == 'POST':
        
        orderData = json.loads(request.data);
        allOrderData = pd.read_csv(orderData['filename']+"_orders.csv")
        menu = pd.read_csv(orderData['filename']+"_menu.csv")
        
        groupedOrderData = allOrderData.groupby('name')['quantity'].sum().to_frame();
        groupedOrderData = groupedOrderData.sort_values(['quantity'] , ascending=False)
        
        mostSoldItems = list(groupedOrderData.head(5).index.values)
        mostSoldItemsCount = list(groupedOrderData.head(5)['quantity'].values)
        leastSoldItems = list(groupedOrderData.tail(5).index.values)
        leastSoldItemsCount = list(groupedOrderData.tail(5)['quantity'].values)
        
        costPrices = []
        sellingPrices = []
        
        for i in list(groupedOrderData.index.values): 
            costPrices.append(int(menu[menu['name'] == i]['cost']))
        
        for i in list(groupedOrderData.index.values): 
            sellingPrices.append(int(menu[menu['name'] == i]['price']))
         
        groupedOrderData['costPrice'] = costPrices
        groupedOrderData['sellingPrice'] = sellingPrices 
        
        groupedOrderData['costPrice'] = groupedOrderData['costPrice'] * groupedOrderData['quantity']
        groupedOrderData['sellingPrice'] = groupedOrderData['sellingPrice'] * groupedOrderData['quantity']
        groupedOrderData['profitEarned'] = groupedOrderData['sellingPrice'] - groupedOrderData['costPrice']
        
        itemNames = list(groupedOrderData.index.values)
        quantitySold = list(groupedOrderData['quantity'].values)
        costPrice = list(groupedOrderData['costPrice'].values)
        sellingPrice = list(groupedOrderData['sellingPrice'].values)
        profitEarned = list(groupedOrderData['profitEarned'].values)

        totalSale = str(groupedOrderData['sellingPrice'].sum());
        totalExpenditure = str(groupedOrderData['costPrice'].sum());
        
             
        orderHours = list(allOrderData['orderHour'].unique())        
        orderHours.sort()        
        orderCountHour = []
        
        for i in list(allOrderData['orderHour'].unique()):
            orderCountHour.append(len(allOrderData[allOrderData['orderHour'] == i]['ordernumber'].unique()))
             
        date_format = "%m/%d/%Y"
        a = datetime.strptime(allOrderData.iloc[0]['date'], date_format)
        b = datetime.strptime(allOrderData.iloc[-1]['date'], date_format)
        totalDays = b - a
        totalDays = int(totalDays.days) + 1;
        
        analysisData = dict()
        
        analysisData['totalSales'] = (totalSale)
        analysisData['totalExpenditures'] = (totalExpenditure)
        
        analysisData['mostSoldItems'] = [str(i) for i in mostSoldItems]
        analysisData['mostSoldItemsCount'] = [str(i) for i in mostSoldItemsCount]
        analysisData['leastSoldItems'] = [str(i) for i in leastSoldItems]
        analysisData['leastSoldItemsCount'] = [str(i) for i in leastSoldItemsCount]
        analysisData['itemNames'] = [str(i) for i in itemNames]; 
        analysisData['quantitySold'] = [str(i) for i in quantitySold]
        analysisData['costPrice'] = [str(i) for i in costPrice]
        analysisData['sellingPrice'] = [str(i) for i in sellingPrice]
        analysisData['profitEarned'] = [str(i) for i in profitEarned]
        analysisData['orderHour'] = [str(i)+":00 PM" if (i > 12) else str(i)+ ":00 AM" for i in orderHours];
        analysisData['orderCountHour'] = [str(i) for i in orderCountHour]
        analysisData['totalDays'] = str(totalDays)
        
        
        return jsonify({'success':True , 'data':json.dumps(analysisData)})
    
    else:
        return jsonify({'success':False})


@app.route('/getTodaysAnalysis', methods=['GET', 'POST'])
def getTodaysAnalysis():
    if request.method == 'POST':
        
        orderData = json.loads(request.data);
        allOrderData = pd.read_csv(orderData['filename']+"_orders.csv")
        menu = pd.read_csv(orderData['filename']+"_menu.csv")
        
        todayOrderData = allOrderData[allOrderData['date'] == orderData['todayDate']]
        
        todayOrderCount = len(todayOrderData['ordernumber'].unique())
        todaySales = int(todayOrderData['price'].sum())
        
        
        allItemNames =  list(todayOrderData.iloc[:]['name'].unique());
        totalQuantityEach = []
        for item in allItemNames:
            totalQuantityEach.append(todayOrderData.loc[todayOrderData['name'] == item]['quantity'].sum())
        
        
        groupedOrderData = todayOrderData.groupby('name')['quantity'].sum().to_frame();
        groupedOrderData = groupedOrderData.sort_values(['quantity'] , ascending=False)
        
        costPrices = []
        sellingPrices = []
        
        for i in list(groupedOrderData.index.values): 
            costPrices.append(int(menu[menu['name'] == i]['cost']))
        
        for i in list(groupedOrderData.index.values): 
            sellingPrices.append(int(menu[menu['name'] == i]['price']))
         
        groupedOrderData['costPrice'] = costPrices
        groupedOrderData['sellingPrice'] = sellingPrices 
        
        groupedOrderData['costPrice'] = groupedOrderData['costPrice'] * groupedOrderData['quantity']
        groupedOrderData['sellingPrice'] = groupedOrderData['sellingPrice'] * groupedOrderData['quantity']
        groupedOrderData['profitEarned'] = groupedOrderData['sellingPrice'] - groupedOrderData['costPrice']
        
    
        totalExpenditure = int(groupedOrderData['costPrice'].sum());
        totalProfit = todaySales - totalExpenditure
        
        itemNames = list(groupedOrderData.index.values)
        quantitySold = list(groupedOrderData['quantity'].values)
        costPrice = list(groupedOrderData['costPrice'].values)
        sellingPrice = list(groupedOrderData['sellingPrice'].values)
        profitEarned = list(groupedOrderData['profitEarned'].values)
        
        
        todaysData = dict()
        
        todaysData['totalOrders'] = str(todayOrderCount);
        todaysData['totalSale'] = str(todaySales);
        todaysData['totalExpenditure'] = str(totalExpenditure)
        todaysData['totalProfit'] = str(totalProfit)
        
        todaysData['allItemNames'] = [str(i) for i in allItemNames];
        todaysData['totalQuantityEach'] = [str(i) for i in totalQuantityEach]
        
        todaysData['itemNames'] = [str(i) for i in itemNames]; 
        todaysData['quantitySold'] = [str(i) for i in quantitySold]
        todaysData['costPrice'] = [str(i) for i in costPrice]
        todaysData['sellingPrice'] = [str(i) for i in sellingPrice]
        todaysData['profitEarned'] = [str(i) for i in profitEarned]
        
        return jsonify({'success':True , 'data':json.dumps(todaysData) })
    
    else:
        return jsonify({'success':False})
    
    
@app.route('/getReviewAnalysis', methods=['GET', 'POST'])
def getReviewAnalysis():
    if request.method == 'POST':
        orderData = json.loads(request.data);
        
        reviewsResponse = requests.get('https://developers.zomato.com/api/v2.1/reviews?res_id='+str(orderData['zomatoId']) , headers ={'Content-Type': 'application/json' , 'user-key': 'd8a7aeb4326557e77200b077a43f9617'})
        
        reviewResponse = json.loads(reviewsResponse.content)    

        reviewData = reviewResponse['user_reviews']    
        reviewDF = json_normalize(reviewData)    
        allReviewText = list(reviewDF['review.review_text'])    
        reviewRatingtext=list(reviewDF['review.rating_text'])    
        reviewRating = list(reviewDF['review.rating'])    
        reviewUserNames = list(reviewDF['review.user.name'])    
        positiveReviews = str(len([i for i in reviewRating if(i > 2.5)]))    
        negativeReivews = str(len([i for i in reviewRating if(i <= 2.5)]))    
        reviewRatingTextCount = []
        
        for i in reviewRatingtext:
                reviewRatingTextCount.append(str(len(reviewDF[reviewDF['review.rating_text'] == i])))
    
        reviewData = dict()
        
        reviewData['totalZomatoReview'] = str(reviewResponse['reviews_count'])
        reviewData['reviewShown'] = str(reviewResponse['reviews_shown'])
        reviewData['allReviewText'] = allReviewText;
        reviewData['reviewRatingtext'] = reviewRatingtext;
        reviewData['reviewRating'] = reviewRating;
        reviewData['reviewUserNames'] = reviewUserNames;
        reviewData['positiveReviews'] = positiveReviews;
        reviewData['negativeReivews'] = negativeReivews;
        reviewData['reviewRatingTextCount'] = reviewRatingTextCount
        

        return jsonify({'success':True , 'data':json.dumps(reviewData) })
    
    else:
        return jsonify({'success':False})


        
@app.route('/setTableCount', methods=['GET', 'POST'])
def setTableCount():
    if request.method == 'POST':
        orderData = json.loads(request.data);
        loginData.loc[loginData["username"]==orderData['username'], "tablecount"] = orderData['tablecount'];
        loginData.to_csv("Login.csv", index=False)
        return jsonify({'success':True})
    
    else:
        return jsonify({'success':False})
         


def main():
    app.run();
        
    
main()    

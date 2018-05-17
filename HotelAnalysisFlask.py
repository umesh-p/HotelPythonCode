from flask import Flask
from flask_cors import CORS, cross_origin
from flask import request
from flask import jsonify

import pandas as pd
import numpy as np
import json
from pandas.io.json import json_normalize
from datetime import datetime
from datetime import timedelta
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
    conn.execute(query)    
    conn.commit()  
    return 'success'

def deleteData(tableName, param ,id):
    
    query = "DELETE from "+str(tableName)+" where "+param+" = "+str(id);
    conn.execute(query)    
    conn.commit()  
    return 'success'
   

#========================================================================================================    
   
@app.route('/login', methods=['GET', 'POST' , 'PUT' , 'DELETE'])
def login():
    loginResponse = json.loads(request.data)
    
    
    if request.method == 'POST':
        userData = c.execute('select name,tablecount,zomatoid from loginData where name = ? and password = ? ' , (loginResponse['username'] ,loginResponse['password'])).fetchall();
        if(len(userData) > 0):
            return jsonify({'success':True , 
                            'data':{ 
                                    'userName' : userData[0][0] , 
                                    'tableCount':userData[0][1],
                                    'zomatoid':userData[0][2]
                                    }, 
                            'message':'valid user'}) 
        else:
            return jsonify({'success':False ,'data':'' ,'message':'Invalid Username or Password'}) 
        
        
    if request.method == 'PUT':
        userName = request.headers['userName']
        updateTableCount = 'update loginData set tablecount = '+str(loginResponse)+' where name = '+'"'+str(userName)+'"' ;
        conn.execute(updateTableCount)    
        conn.commit();
        return jsonify({'success':True , 'data' : '' })
        
#========================================================================================================    
 
    
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
    
#========================================================================================================    

@app.route('/category', methods=['GET', 'POST' , 'PUT' , 'DELETE'])
def category():
    
    table = 'foodcategories'
    category = (request.data).decode('utf-8')
    print(category)
    if request.method == 'GET':
        data =  selectData(table)         
        return jsonify({'success':True , 'data':data })    
    
    if request.method == 'POST':
        insertCategory = "insert into foodcategories (name) values ("+str(category)+")";   
        conn.execute(insertCategory)    
        conn.commit();
        return jsonify({'success':True , 'data' : 'success' })
        
#========================================================================================================    
    
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
                    
                data[index]['materialUsed'] = matDel;
                index = index + 1
            
            return jsonify({'success':True , 'data':data })    
        return jsonify({'success':True , 'data':[] })  
    
    if request.method == 'POST':
        response = dict(json.loads(request.data))
        
        response['isfavourite'] = str(response['isfavourite'])
        response['isdisabled'] = str(response['isdisabled'])
        
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
        
        response['isfavourite'] = str(response['isfavourite'])
        response['isdisabled'] = str(response['isdisabled'])
        
        print(response)    
        
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
#========================================================================================================  
    
@app.route('/getReviewAnalysis', methods=['GET', 'POST'])
def getReviewAnalysis():
    if request.method == 'POST':
        orderData = json.loads(request.data);
        
        reviewsResponse = requests.get('https://developers.zomato.com/api/v2.1/reviews?res_id='+str(orderData['zomatoid']) , headers ={'Content-Type': 'application/json' , 'user-key': 'd8a7aeb4326557e77200b077a43f9617'})
        reviewResponse = json.loads(reviewsResponse.content)    

        reviewData = reviewResponse['user_reviews']    
        reviewDF = json_normalize(reviewData)       
        reviewRating = list(reviewDF['review.rating'])    
        positiveReviews = str(len([i for i in reviewRating if(i > 2.5)]))    
        negativeReivews = str(len([i for i in reviewRating if(i <= 2.5)]))    
        
        reviewResponse['positiveReviews'] = positiveReviews;
        reviewResponse['negativeReivews'] = negativeReivews;
        
        return jsonify({'success':True , 'data':json.dumps(reviewResponse) })
    
    else:
        return jsonify({'success':False})
    
#========================================================================================================  

@app.route('/saveOrder', methods=['GET', 'POST'])
def submitOrder():
    
    userName = request.headers['userName']
    table = userName+'Orders'
    orderedItemsTable = userName+'OrderItems'

    if request.method == 'POST':
        orderData = json.loads(request.data);  
        orderedItems = orderData['orderedItems']
        del orderData['orderedItems']
        
        allKeys  = tuple(orderData.keys())       
        allData = tuple(orderData.values())
        data = insertData(table ,allKeys, allData)
        keys = list(orderedItems[0].keys())
        keys.remove('sellingprice')
        keys.append('orderid')

        allvalues = "";
        for item in orderedItems:
            del item['sellingprice']
            values = list(item.values())
            values.append(data)
            allvalues = allvalues +","+str(tuple(values))

        insertData(orderedItemsTable ,tuple(keys), allvalues.strip(',')) 
        return jsonify({'success':True})
    else:
        return jsonify({'success':False})

#========================================================================================================
        
    
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboardData():
    
    userName = request.headers['userName']
    table = userName+'Orders'
    orderedItemsTable = userName+'OrderItems'
    
    responseObj = {};
    if request.method == 'GET':
        
        orderData = pd.read_sql_query("SELECT * FROM "+table+"", conn)
        orderItemData = pd.read_sql_query("SELECT * FROM "+orderedItemsTable+"", conn)
        
        responseObj['totalOrders'] = len(orderData)
        responseObj['tableOrderCount'] = len(orderData[orderData['ordermethod'] == 'tableorder'])
        responseObj['parcelOrderCount'] = len(orderData[orderData['ordermethod'] == 'parcel'])
        responseObj['OnlineOrderCount'] = len(orderData[orderData['ordermethod'] == 'online'])
        responseObj['totalSales'] = sum(orderData['totalbillamt'])
        
        allPaymentMethods = list(orderData['paymentmethod'].unique())
        paymentMethodCount = []
        
        for i in allPaymentMethods:
            paymentMethodCount.append(str(len(orderData[orderData['paymentmethod'] == i])))
             
        responseObj['allPaymentMethods'] = allPaymentMethods;
        responseObj['allPaymentCount'] = paymentMethodCount;
        
        today = datetime.now().date();
        lastTenDays = [];
        orderCount = [];
        
        for i in range(0,10):
            date = (str(today - timedelta(days=i)))
            lastTenDays.append(str(date))
            orderCount.append(len(orderData[(orderData['year'] == int(date[:4])) & (orderData['month'] == int(date[5:7])) & (orderData['date'] == int(date[-2:]))]))
            
        responseObj['lastTenDays'] = lastTenDays[::-1];
        responseObj['orderCount'] = orderCount[::-1];
        
        return jsonify({'success':True, 'data':json.dumps(responseObj) })
    
    else:
        return jsonify({'success':False})
#========================================================================================================

@app.route('/dailyPlates', methods=['GET', 'POST' , 'PUT' , 'DELETE'])
def dailyPlates():
    
    userName = request.headers['userName']
    table = userName+'DailyPlates'
    
    if request.method == 'GET':
        today = str(datetime.now().date());
        print('SELECT * from '+table+' where dayDate = '+today)
        cursor = conn.execute('SELECT * from '+table+' where dayDate = "'+today+'"')
        dataRows = cursor.fetchall();
        columns = [d[0] for d in cursor.description]
        data = [dict(zip(columns, row)) for row in dataRows]        
        return jsonify({'success':True , 'data':data })    
    
    if request.method == 'POST':
        response = dict(json.loads(request.data))
        allKeys  = tuple(response.keys())       
        allData = tuple(response.values())
        data = insertData(table ,allKeys, allData) 
        return jsonify({'success':True , 'data' : data })

#========================================================================================================


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



def main():
    app.run();
        
    
main()    

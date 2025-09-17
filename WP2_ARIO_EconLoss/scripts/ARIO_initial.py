# -*- coding: utf-8 -*-
"""
This is a file for MRIO test.
"""
###
#%%
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
#%%

# Function to calculate production output
def production(StockMat, COE_A, IOV_t, COE_VA, ORDER, IOX_0):
    # Calculate output driven by stock and value-added
    Stock_X = StockMat / COE_A
    V_X = IOV_t / COE_VA
    O_X = np.sum(ORDER, axis=1, keepdims=True).T
    # temp = 1.25 * IOX_0[np.newaxis, :]   
    # Stock_X[mat_key] = temp[mat_key] # only important sector goes into function
    # Return minimum output based on stock, VA, and order
    return np.min(np.vstack([Stock_X, V_X, O_X]), axis=0)

# Function to calculate maximum production output
def production_max(StockMat, COE_A, IOV_t, COE_VA):
    Stock_X = StockMat / COE_A
    V_X = IOV_t / COE_VA
    # temp = 1.25 * IOX_0[np.newaxis, :]   
    # Stock_X[mat_key] = temp[mat_key] # only important sector goes into function
    # Return minimum output between stock and value-added constraints
    return np.min(np.vstack([Stock_X, V_X]), axis=0)

# Function to determine overproduction sign
def over_prod_sign_fun(StockMat, COE_A, IOV_t, COE_VA, ORDER, IOX_0):
    # Initialize the result matrix
    result = np.zeros((UU, R_S))
    
    # Compute constraints for stock and value-added
    Stock_X = StockMat / COE_A
    V_X = IOV_t / COE_VA
    O_X = np.sum(ORDER, axis=1, keepdims=True).T
    
    S_OX = np.vstack([Stock_X, O_X])
    
    # Overproduction checks
    V1U = np.tile(V_X, (S_OX.shape[0], 1)) < S_OX
    result[0, np.sum(V1U, axis=0) == S_OX.shape[0]] = 1

    V1D = np.tile(V_X, (S_OX.shape[0], 1)) > S_OX
    result[0, np.sum(V1D, axis=0) > 0] = -1
    
    # Return the result multiplied by the absolute difference between OX and VX
    return result * (np.abs(O_X - V_X) / IOX_0)

# def Transport_factor(t, total_periods):
#     # Trans constrain diminish over time. At the end, it would be 1 (no constrain)
#     return min(1, t / total_periods)
#%%

#%%
#Regionas and Sectors
REG = 4  # Number of regions
SEC = 3  # Number of sectors
R_S = REG * SEC  # Region and sector combinations
S_R = REG * SEC
TIM = 31  # Number of periods
UU = 1  # Row of value added

# Column names for regions and sectors
col_all = ["R1S1", "R1S2", "R1S3", "R2S1", "R2S2", "R2S3", 
           "R3S1", "R3S2", "R3S3", "R4S1", "R4S2", "R4S3", 
           "R1F", "R2F", "R3F", "R4F"]
col_R_S = col_all[:R_S]

# Read the input MRIO table
MRIOTPath = "Input/MRIOTtest.xlsx"
MRIOT = pd.read_excel(MRIOTPath, sheet_name=0, header=None, usecols="C:R", skiprows=2)
MRIOT.columns = col_all
MRIOT = MRIOT.to_numpy()

#%%

#%%
# Extract relevant matrices from MRIOT
# Variables:All uppercase variables are exogenous
IOZ_0 = MRIOT[0:(REG * SEC), 0:(REG * SEC)]  # Z Matrix (intermediate use)


IOF_0 = MRIOT[0:(REG * SEC), (REG * SEC):(REG * SEC + REG)]  # Final demand matrix
IOV_0 = MRIOT[(REG * SEC):(REG * SEC + UU), 0:(REG * SEC)]  # Value-added
IOX_0 = np.sum(IOZ_0, axis=0) + np.sum(IOV_0, axis=0)  # Total output 

# Initialize matrices for the time period
IOX_TIM = np.zeros((TIM, R_S))
IOX_TIM_max = np.zeros((TIM, R_S))

# Compute stock and production coefficients
I_Sum = np.tile(np.eye(SEC), (1, REG))  # I Matrix 
IOZ_C = np.dot(I_Sum, IOZ_0)  # Z Combine regions 
Z_Dis = IOZ_0 / np.tile(IOZ_C, (REG,1)) # Distribute toal intermediate use for each sector into each region

StockMat = 6*IOZ_C  # Stock = 6 times of intermediate use
StockObj = StockMat + IOZ_C # Objected stock
#np.repeat(np.arange(3), 4) 每行重复四次
IOF_C = np.dot(I_Sum, IOF_0)  # F Combine regions 
F_Dis = IOF_0 / IOF_C[np.repeat(np.arange(SEC), REG), :] # Similar to Z_Dis
IOF_TIM = np.repeat(IOF_0[:, :, np.newaxis], TIM, axis=2) #  F x TIME

# Coefficients for production calculations
COE_A = np.dot(IOZ_C, np.diag(1 / IOX_0))  # Coefficient A for combined Z
COE_VA = np.dot(IOV_0, np.diag(1 / IOX_0)) # Coefficient VA 

# # Overproduction parameters
Over_PROD = np.ones((UU, REG * SEC))  # OverProd
Over_PRODSign = np.zeros((UU, REG * SEC))  # OverProdSign
Over_PRODStep = np.full((UU, REG * SEC), 0.25 / TIM)  #  the ability of overproduction rise 25% in step 52
Over_PRODUpbd = np.full((UU, REG * SEC), 1.25)  # OverProduction upper boundary, says the ability of overproduction could reach maxmium of 25%

# Initialize order matrix
ORDER = np.hstack((IOZ_0, IOF_0)) # Order Matrix (Z+F)

#%%
#以上程序都检查完毕
#%%
#Model runs

# Initialize constraints and calculate max production
Labor_Cons = np.ones((SEC, REG, TIM))
Transport_Cons_TIM = np.ones((S_R, REG, TIM)) # no constrain

Start_Time = time.time()

#%%

#%%
# 循环开始
for t in range(1, TIM):
    print(t)
    # t = 1
    IOV_Cons = np.zeros((UU, R_S)) # (UU=1 means only 1 row of VA)
    IOV_Cons[0, ] = Labor_Cons[:, :, t-1].reshape(1, -1)  # Constrain of value_added
    
    # # Calculate production under constraints
    IOV_t = IOV_0 * IOV_Cons * Over_PROD #Constrain of IOV
    IOX_t_max = production_max(StockMat, COE_A, IOV_t, COE_VA) #Max output under constrain of value_added
    IOX_t_max = IOX_t_max.reshape(1, -1)
    
    # Actual production based on order and constraints
    IOX_t = production(StockMat, COE_A, IOV_t, COE_VA, ORDER, IOX_0) #actual production in t, depends on order and 
    IOX_t = IOX_t.reshape(1, -1)
    
    # Max distribute ability = 'share of each order in total order' * 'Max output under constrain'
    IOX_t_Dis_max = (ORDER / np.sum(ORDER, axis=1, keepdims=True)) * np.tile(IOX_t_max, (R_S + REG, 1)).T
    
    # Actual distribute of Order
    IOX_t_Dis = (ORDER / np.sum(ORDER, axis=1, keepdims=True)) * np.tile(IOX_t, (R_S + REG, 1)).T
    
    # Stock Change
    StockUse = np.tile(IOX_t, (SEC, 1)) * COE_A # Stockuse = actual production * COE_A
    StockAdd = np.dot(I_Sum, IOX_t_Dis[:, :R_S]) # Actual distribute of Order
    StockMat = StockMat - StockUse + StockAdd 
    StockGap = StockObj - StockMat
    StockGap[StockGap < 0] = 0
    
    # Adjust order distribution based on transport constraints
    # Trans_factor = Transport_factor(t, TIM)
    
    Trans_T = Transport_Cons_TIM[:, :, t-1]
    Trans_T = Trans_T[:, np.repeat(np.arange(REG), SEC)] #对Trans_T进行扩展 扩展部门
    # print(Trans_T)

    
    
    # Adjust distribution under transport constraints 不要改变数组的维度 不同的维度
    min_IOV_Cons = np.min(IOV_Cons, axis=0)
    Trans_Z_Dis = Z_Dis * Trans_T * np.tile(min_IOV_Cons, (R_S, 1)) # if Trans_T and IOV_cons = 1, Trans_Z_Dis = Z_Dis
    Trans_Z_Dis_sum = np.dot(I_Sum, Trans_Z_Dis) #为什么要加总再除
    ACTUAL_Z_Dis = Trans_Z_Dis / np.tile(Trans_Z_Dis_sum, (REG, 1)) #Actual Z_Dis
    
    # Final actual order (Fixed np.repeat syntax)
    ORDER[:, :R_S] = np.tile(StockGap, (REG, 1)) * ACTUAL_Z_Dis
    
    Order_I_Z = ORDER[:, :R_S] #order for initial intermidate use
    Order_T_Z = IOZ_0 * Trans_T #order for trans constrin intermidate use
    Order_I_Z = np.where(Order_T_Z < Order_I_Z, Order_T_Z, Order_I_Z)
    ORDER[:, :R_S] = Order_I_Z
    
    # Adjust F distribution under transport constraints
    Trans_T = Transport_Cons_TIM[:, :, t-1]
    Trans_F_Dis = F_Dis * Trans_T * np.tile(min_IOV_Cons[:, np.newaxis], (1, REG)) #np.repeat(min_IOV_Cons, REG, axis=0).T 
    Trans_F_Dis_sum = np.dot(I_Sum, Trans_F_Dis)
          
    
    #all good above
    #Order_I_F = np.dot(I_Sum, IOF_TIM[:, :, t])
    #ORDER[:, R_S:] = np.repeat(Order_I_F, REG).reshape(R_S, -1) * ACTUAL_F_Dis
    
    Order_I_F = ORDER[:, R_S:]
    Order_T_F = IOF_0 * Trans_T
    Order_I_F = np.where(Order_T_F < Order_I_F, Order_T_F, Order_I_F)
    ORDER[:, R_S:] = Order_I_F
    
    # Overproduction
    Over_PRODSign = over_prod_sign_fun(StockMat, COE_A, IOV_t, COE_VA, ORDER, IOX_0)
    
    # 更新过度生产状态
    Over_PROD += Over_PRODSign * Over_PRODStep
    Over_PROD[Over_PROD < 1] = 1
    Over_PROD[Over_PROD > Over_PRODUpbd] = Over_PRODUpbd[Over_PROD > Over_PRODUpbd]
    
    # 记录生产情况
    IOX_TIM[t-1, :] = IOX_t
    IOX_TIM_max[t-1, :] = IOX_t_max
    
    # Production Ratio Visualization
    production_ratio = np.sum(IOX_TIM, axis=1) / np.sum(IOX_TIM_max, axis=1) #这改一下
    
    plt.figure(figsize=(10, 6))
    plt.plot(range(1, TIM + 1), production_ratio, marker='o', linestyle='-', color='b', label="Production Ratio")
    plt.xlabel("Time Period")
    plt.ylabel("Production Ratio (Actual / Max)")
    plt.title("Production Ratio Over Time")
    plt.legend()
    plt.grid(True)
    plt.show()    
    
    #实际输出的时候是要把结果直接输出到文件里csv 以时间t为后缀
    
    #print(f"Scenario: {Scenario}")
    print(f"PRODuction ratio: {np.sum(IOX_t) / np.sum(IOX_0)}")
    # print(f"Elapsed time: {time.time() - Start_Time}")
print("end")

#%%
























# %%

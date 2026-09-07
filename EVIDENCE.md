Created a Test customer 
![alt text](image-2.png)

got the current plan status
![alt text](image-3.png)


created a checkout session
![alt text](image-4.png)

The checkout status 
![alt text](image-5.png)

The URL opened in the payement area
![alt text](image-7.png)

Updated to Pro Status
![alt text](image-6.png)



## Idempotency Test on terminal 

First request
Generated specific idempotency-key with the specific tenant
Second request demanded the same, it returned the same id:1, instead of making a new one

![alt text](image-8.png)

# Quota Test


![alt text](image-9.png)

Server Flags it successfully

![alt text](image-10.png)
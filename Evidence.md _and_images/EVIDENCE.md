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

## Quota alert added

### Quota Warning at 80% Usage

This request caused the id:2's quota to increase
```
Invoke-RestMethod 
    -Uri "http://localhost:8000/tenants/2/usage" `
    -Method Post `
    -ContentType "application/json" `
    -Body '{"usage_type":"api_call","quantity":80,"idempotency_key":"alert-test-80"}'`
```
This Trigger alert was produce when the manual endpoint was called upon

```
Invoke-RestMethod -Uri "http://localhost:8000/admin/alerts" -Method Post

```
The result:

![alt text](image-11.png)

### Quota Critical alert at 100% usage
This user had used 90% of their tokens by adding 10 more token usage
```
    Invoke-RestMethod `
        -Uri "http://localhost:8000/tenants/3/usage" `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"usage_type":"api_call","quantity":10,"idempotency_key":"alert-test-100"}'
```

![alt text](image-12.png)

This warning was issued; two warnings, 

One for the 80% usage warning and one critical usage warning

![alt text](image-13.png)

Output
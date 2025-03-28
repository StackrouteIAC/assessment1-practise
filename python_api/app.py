from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uvicorn
import mysql.connector
from decimal import Decimal
import os

app = FastAPI()

# Database configuration
DB_CONFIG = {
    "host": os.environ.get("MYSQL_HOSTNAME", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DB", "sample_db")
}

# Pydantic models for request/response
class OrderItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float

class OrderCreate(BaseModel):
    customer_id: int
    order_items: List[OrderItem]

class Order(BaseModel):
    order_id: int
    customer_id: int
    order_date: datetime
    total_amount: float

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

@app.get("/orders", response_model=List[Order])
def get_orders():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM orders")
        orders = cursor.fetchall()
        return orders
    finally:
        cursor.close()
        conn.close()

@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
        order = cursor.fetchone()
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return order
    finally:
        cursor.close()
        conn.close()

@app.post("/orders", response_model=Order)
def create_order(order: OrderCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verify customer exists
        cursor.execute("SELECT customer_id FROM customers WHERE customer_id = %s", 
                      (order.customer_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Customer not found")

        # Calculate total amount
        total_amount = sum(item.quantity * item.unit_price for item in order.order_items)

        # Create order
        cursor.execute(
            "INSERT INTO orders (customer_id, total_amount) VALUES (%s, %s)",
            (order.customer_id, total_amount)
        )
        order_id = cursor.lastrowid

        # Create order items
        for item in order.order_items:
            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
                "VALUES (%s, %s, %s, %s)",
                (order_id, item.product_id, item.quantity, item.unit_price)
            )

        conn.commit()

        # Fetch and return the created order
        cursor.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
        new_order = cursor.fetchone()
        
        return {
            "order_id": new_order[0],
            "customer_id": new_order[1],
            "order_date": new_order[2],
            "total_amount": float(new_order[3])
        }

    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

@app.delete("/orders/{order_id}")
def delete_order(order_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Delete order items first (due to foreign key constraint)
        cursor.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))
        
        # Delete the order
        cursor.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Order not found")
        
        conn.commit()
        return {"message": "Order deleted successfully"}
    
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

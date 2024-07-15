from fastapi import FastAPI
import uvicorn
from fastapi.responses import JSONResponse
from fastapi import Request
import database as db
import logging
import extraa_functions as helper

logging.basicConfig(level=logging.INFO)
inprogress_order = {}

app = FastAPI()

@app.post("/")
async def handle_request(request: Request):
    payload = await request.json()
    intent = payload["queryResult"]["intent"]["displayName"]
    parameters = payload["queryResult"]["parameters"]
    output_contexts = payload["queryResult"]["outputContexts"]

    session_id = helper.extract_session_id(output_contexts[0]["name"])

    intent_handler_dictionary = {
        "track.order - context:ongoing-tracking": track_order,
        "order.add-context: ongoing-order": add_order,
        "order.complete-context: ongoing-order": complete_order,
        "order.remove-context: ongoing-order": remove_order,
        "new.order": new_order
    }

    return intent_handler_dictionary[intent](parameters, session_id)


def save_to_db(order: dict):
    next_order_id = db.get_next_order_id()

    for food_item, quantity in order.items():
        rcode = db.insert_order_item(
            food_item,
            quantity,
            next_order_id
        )

        if rcode == -1:
            return -1

    db.insert_order_tracking(next_order_id, "in progress")

    return next_order_id


def complete_order(parameters: dict, session_id: str):
    if session_id not in inprogress_order:
        fulfillment_text = "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
    else:
        order = inprogress_order[session_id]
        order_id = save_to_db(order)

        if order_id == -1:
            fulfillment_text = "Sorry, I couldn't process your order due to a backend error. " \
                               "Please place a new order again"

        else:
            order_total = db.get_total_order_price(order_id)
            fulfillment_text = f"Awesome. We have placed your order. " \
                             f"Here is your order id # {order_id}. " \
                             f"Your total price is {order_total} which you can pay at the time of delivery!"

        del inprogress_order[session_id]

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def add_order(parameters: dict, session_id: str):
    food_item = parameters["food-item"]
    quantities = parameters["number"]

    if len(food_item) != len(quantities):
        fulfillment_text = "Sorry I didn't understand. Can you please specify food items and quantities clearly."
    else:
        new_food_dict = dict(zip(food_item, quantities))

        if session_id in inprogress_order:
            currrnt_food_dict = inprogress_order[session_id]
            currrnt_food_dict.update(new_food_dict)
            inprogress_order[session_id] = currrnt_food_dict
        else:
            inprogress_order[session_id] = new_food_dict

        order_str = helper.get_str_from_food_dict(inprogress_order[session_id])
        fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def remove_order(parameters: dict, session_id: str):
    if session_id not in inprogress_order:
        return JSONResponse(content={
            "fulfillmentText": "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
        })

    food_items = parameters["food-item"]
    current_order = inprogress_order[session_id]

    no_such_item = []
    removed_item = []

    for item in food_items:
        if item not in current_order:
            no_such_item.append(item)
        else:
            removed_item.append(item)
            del current_order[item]

    fulfillment_text = ""
    if len(removed_item) > 0:
        fulfillment_text = f'Removed {",".join(removed_item)} from your order!'
    if len(no_such_item) > 0:
        fulfillment_text = f' Your current order does not have {",".join(no_such_item)}'
    if len(current_order.keys()) == 0:
        fulfillment_text += " Your order is empty!"
    else:
        order_str = helper.get_str_from_food_dict(current_order)
        fulfillment_text += f" Here is what is left in your order: {order_str}"

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def track_order(parameters: dict, session_id: str):
    order_id = parameters["number"][0] if isinstance(parameters["number"], list) else parameters["number"]
    order_status = db.get_order_status(int(order_id))

    if order_status:
        fulfillment_text = f"The order status for order is {int(order_id)} is: {order_status}"
    else:
        fulfillment_text = f"No order found with order id: {int(order_id)}"

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


def new_order(parameters: dict, session_id: str):
    inprogress_order[session_id] = {}
    fulfillment_text = "Starting new order. Specify food items and quantities. For example, you can say, 'I would like to order two pizzas and one mango lassi.' Also, we have only the following items on our menu: Pav Bhaji, Chole Bhature, Pizza, Mango Lassi, Masala Dosa, Biryani, Vada Pav, Rava Dosa, and Samosa."

    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })


if __name__ == "__main__":
    uvicorn.run(app, port=8000)

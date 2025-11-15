import asyncio
import dotenv
from browser_use import Agent, Browser, ChatBrowserUse

from Backend.data.utils import retrieve_medications, _read_json, USER_DATA_FILE

# dotenv.load_dotenv()

STORE = {
    "base_url": "https://www.drogist.nl/",
    "locale_hint": "Site is in Dutch; you can use the search field.",
}


def load_user(user_id: str) -> dict:
    users = _read_json(USER_DATA_FILE)
    for u in users:
        if u.get("user_id") == user_id:
            full_name = u.get("full_name", "")
            names = full_name.split()
            return {
                "user_id": u.get("user_id", ""),
                "age": u.get("age", ""),
                "username": u.get("username", ""),
                "full_name": full_name,
                "first_name": names[0] if names else "",
                "last_name": names[-1] if names else "",
                "password": u.get("password", ""),
                "email": u.get("email", ""),
                "phone": u.get("phone_number", ""),
                "phone_number": u.get("phone_number", ""),
                "street": u.get("street", ""),
                "house_number": u.get("house_number", ""),
                "street_full": f"{u.get('street','')} {u.get('house_number','')}".strip(),
                "postal_code": u.get("post_code", ""),
                "post_code": u.get("post_code", ""),
                "city": u.get("city", ""),
                "country": "Netherlands",
                "doctor_email": u.get("doctor_email", ""),
                "cvv": u.get("cvv", ""),
                "expiry_date": u.get("expiry_date", ""),
                "credit_card_number": u.get("credit_card_number", ""),
                "gender": u.get("gender", ""),
            }
    raise ValueError(f"User ID {user_id} not found in personal_data.json")


def build_task(user, product, store) -> str:
    return f"""
You are a careful shopping assistant automating a browser.

GOAL
- On {store['base_url']} search for: "{product['name']}".
- Select an in-stock product that clearly matches the requested name and strength (no substitutes).
- Set quantity to 1 and add to cart.
- Proceed to checkout and fill shipping details using the info below.
- STOP BEFORE PAYMENT and summarize the checkout state.

USER DETAILS
- First name: {user['first_name']}
- Last name: {user['last_name']}
- Email: {user['email']}
- Phone: {user['phone']}
- Street: {user['street']}
- Postal code: {user['postal_code']}
- House number: {user['house_number']}
- City: {user['city']}
- Country: {user['country']}
- Credit card number: {user['credit_card_number']}
- Expiry date: {user['expiry_date']}
- CVV: {user['cvv']}
- Initials: {user['first_name'][0]}{user['last_name'][0]}

CONSTRAINTS
- Stay on drogist.nl
- Accept minimal cookies if banner appears
- If product not found, do not substitute — report failure

OUTPUT
- success/failure, cart item, price, quantity, subtotal, shipping method, blockers, page URL
"""


def find_medication_entry(user_id: str, drug_name: str) -> dict:
    """Return the user's medication entry matching drug_name (case-insensitive)."""
    meds = retrieve_medications(user_id)
    if not meds:
        raise ValueError(f"No medications found for user {user_id}")

    name = drug_name.lower().strip()

    for med in meds:
        if med.get("drug_name", "").lower().strip() == name:
            return med

    available = [m.get("drug_name") for m in meds]
    raise ValueError(f"Medication '{drug_name}' not found. Available: {available}")


async def run_checkout(user_id: str, drug_name: str):
    user = load_user(user_id)
    product = {"name": drug_name, "quantity": 1}

    browser = Browser()
    llm = ChatBrowserUse()

    agent = Agent(
        task=build_task(user, product, STORE),
        llm=llm,
        browser=browser,
    )
    history = await agent.run()
    return history


if __name__ == "__main__":
    asyncio.run(run_checkout(user_id="1", drug_name="Aspirin"))

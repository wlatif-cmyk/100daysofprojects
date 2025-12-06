from flask import Flask, render_template, request
import requests

app = Flask(__name__)

# api key plz dont steal plz im poor
API_KEY = "dfeadfc24c1ece067cb164a9"

BASE_URL = "https://v6.exchangerate-api.com/v6/{}/latest/{}"

# A small list of currencies to keep things simple
CURRENCIES = ["USD", "EUR", "GBP", "CAD", "JPY", "AUD", "INR"]


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None

    if request.method == "POST":
        amount_text = request.form.get("amount", "").strip()
        from_currency = request.form.get("from_currency", "USD")
        to_currency = request.form.get("to_currency", "EUR")

        # validate amount
        try:
            amount = float(amount_text)
            if amount < 0:
                raise ValueError
        except ValueError:
            error = "Amount must be a positive number."
            return render_template(
                "index.html",
                currencies=CURRENCIES,
                result=result,
                error=error
            )

        # call the API
        try:
            url = BASE_URL.format(API_KEY, from_currency)
            response = requests.get(url, timeout=10)
            data = response.json()
        except Exception:
            error = "Could not reach the exchange rate service."
            return render_template(
                "index.html",
                currencies=CURRENCIES,
                result=result,
                error=error
            )

        # check API response
        if response.status_code != 200 or data.get("result") != "success":
            error_type = data.get("error-type", "unknown error")
            error = f"Exchange rate API error: {error_type}"
            return render_template(
                "index.html",
                currencies=CURRENCIES,
                result=result,
                error=error
            )

        rates = data.get("conversion_rates", {})
        if to_currency not in rates:
            error = "That currency is not available."
        else:
            rate = rates[to_currency]
            converted = round(amount * rate, 4)
            result = {
                "amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": rate,
                "converted": converted,
            }

    return render_template(
        "index.html",
        currencies=CURRENCIES,
        result=result,
        error=error
    )


if __name__ == "__main__":
    app.run(debug=True)

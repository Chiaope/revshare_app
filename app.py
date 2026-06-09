import json
from flask import Flask, render_template, request
from dotenv import load_dotenv
from databricks import sql
import logging
import os

# from databricks.sdk import WorkspaceClient

secondary_sales_question = "Is there a secondary owner assigned to this client profile? If yes, please specify."
secondary_sales_ignore_answer = "No, there is no secondary owner"
internal_secondary_sales_question = (
    "T-365 Rev-Share P&L (FPOV) from Secondary Sales person"
)
internal_primary_sales_question = "T-365 Rev-Share P&L (FPOV) from Primary Sales person"

question_ordered = [
    "status",
    "submitDate",
    "responder",
    "response_id",
    "external_score",
    "internal_score",
    "total_score",
    "Who is the salesperson (Primary owner) completing this form?",
    "Is there a secondary owner assigned to this client profile? If yes, please specify.",
    "What is the client’s company registered name?",
    "What is the client's company registration number?",
    "What is the client’s company registered jurisdiction?",
    "How long has the client’s company been in operation?",
    "What is the client’s group structure (including parent and subsidiaries, if applicable)?",
    "Is the client publicly listed? If yes, where is it listed?",
    "What is the client’s primary regulator?",
    "What is the client’s associated license number?",
    "Does the client currently have any license applications in progress?",
    "Where are most of the client’s active end clients located?",
    "Is the client willing to provide financial information?",
    "What is the client’s primary business activity?",
    "Has the Sales team previously submitted this client’s data to Finalto for any revenue-sharing proposal or trade data analysis? If yes, when was the most recent submission?",
    "Do the client’s parent company or subsidiaries have any current or past relationships with Finalto? If yes, please specify the type of relationship.",
    "If yes, please provide the Finalto account number.",
    "Does the client currently have any revenue-sharing or profit-sharing arrangements with other liquidity providers?",
    "Profit-sharing ratio",
    "Settlement terms",
    "Any special conditions",
    "How is the client’s liquidity setup structured?",
    "If there are multiple liquidity providers, please list them.",
    "How would you best describe the client’s trade flow?",
    "Does the client operate an internal trading or risk management desk?",
    "Is the client able to provide end-client tagging (e.g., End-Tag or unique client ID)?",
    "Would the client be open to collaborating with us to optimize flow segmentation, where specific client groups or trading profiles are managed under different execution setups (e.g., differentiated pricing or accounts)?",
    "Is the client open to implementing a Minimum Account Holding (MAH) on the revenue-sharing account?",
    "What is the client’s fund structure?",
    "Is the client willing to provide trade data for analysis of trading behavior?",
    "Is the client willing to provide collateral to cover potential negative rebate balances under the revenue-sharing arrangement?",
    "What is the client’s preferred settlement structure?",
    "What is the client’s preferred profit-sharing settlement frequency?",
    "What NOP size is the client targeting?",
    "Is the client open to a profit holdback or reserve mechanism?",
    "Attachments",
]

enable_edit_status = "Passed (1A) -  Pending on Risk KYC"
base_available_status = [
    "Rejected (1B)",
    "Rejected (1B) - Others",
    "Rejected (1B) - Risk KYC score is too low",
    "Rejected (1B) - Asked Sales to resubmit",
    "Passed (1B) - Pending on DA",
]
offerings_available_status = [
    "Rejected (2A) - Unsatisfactory Trading Performance",
    "Rejected (2A) - Data Quality Concerns",
    "Rejected (2A) - Strategy / Portfolio Misalignment",
    "Rejected (2A) - Others",
    "Passed (2A) - 10% (Client)/2W",
    "Passed (2A) - 10% (Client)/SUT",
    "Passed (2A) - 20% (Client)/2W",
    "Passed (2A) - 20% (Client)/SUT",
    "Passed (2A) - 30% (Client)/2W",
    "Passed (2A) - 30% (Client)/SUT",
    "Passed (2A) - 40% (Client)/2W",
    "Passed (2A) - 40% (Client)/SUT",
    "Passed (2A) - 50% (Client)/2W",
    "Passed (2A) - 50% (Client)/SUT",
    "Passed (2A) - 60% (Client)/2W",
    "Passed (2A) - 60% (Client)/SUT",
    "Passed (2A) - 70% (Client)/2W",
    "Passed (2A) - 70% (Client)/SUT",
    "Passed (2A) - Others",
]
post_offerings_available_status = [
    "Rejected (2B) - Client rejects the offer",
    "Completed - 10% (Client)/2W",
    "Completed - 10% (Client)/SUT",
    "Completed - 20% (Client)/2W",
    "Completed - 20% (Client)/SUT",
    "Completed - 30% (Client)/2W",
    "Completed - 30% (Client)/SUT",
    "Completed - 40% (Client)/2W",
    "Completed - 40% (Client)/SUT",
    "Completed - 50% (Client)/2W",
    "Completed - 50% (Client)/SUT",
    "Completed - 60% (Client)/2W",
    "Completed - 60% (Client)/SUT",
    "Completed - 70% (Client)/2W",
    "Completed - 70% (Client)/SUT",
    "Completed - Others",
]

internal_form_questions = [
    {
        "label": "T-365 Rev-Share P&L (FPOV) from Primary Sales person",
        "name_attr": "T-365 Rev-Share P&L (FPOV) from Primary Sales person",
        "input_type": "dropdown",
        "options": [
            "Contribute over $1m to Finalto",
            "Contribute between $500k to $1m to Finalto",
            "Contribute between $0 to $500k to Finalto",
            "Making Finalto a loss between $0 to -$500k",
            "Making Finalto a loss between -$500k to -$1m",
            "Making Finalto a loss over $1m",
        ],
        "required": True,
    },
    {
        "label": "T-365 Rev-Share P&L (FPOV) from Secondary Sales person",
        "name_attr": "T-365 Rev-Share P&L (FPOV) from Secondary Sales person",
        "input_type": "dropdown",
        "options": [
            "Contribute over $1m to Finalto",
            "Contribute between $500k to $1m to Finalto",
            "Contribute between $0 to $500k to Finalto",
            "Making Finalto a loss between $0 to -$500k",
            "Making Finalto a loss between -$500k to -$1m",
            "Making Finalto a loss over $1m",
        ],
        "required": True,
    },
    {
        "label": "C-board member history",
        "name_attr": "C-board member history",
        "input_type": "dropdown",
        "options": [
            "Any one of the C-board members has disciplinary record, bankruptcy record",
            "Any one of the C-board members is/was a board member of listed company",
            "CEO,COO both are/were a board member of listed company",
            "No reliable public record found",
        ],
        "required": True,
    },
    {
        "label": "Client's business type according to license number",
        "name_attr": "Client's business type according to license number",
        "input_type": "dropdown",
        "options": [
            "Market Maker / Principal",
            "Hybrid (A-book + B-book)",
            "Pure STP / Agency",
            "Client does not hold any required regulatory license",
            "No reliable public record found",
            "Others",
        ],
        "required": True,
    },
    {
        "label": "If there is past relationship, what is the results",
        "name_attr": "If there is past relationship, what is the results",
        "input_type": "dropdown",
        "options": [
            "Yes- Revenue Share Deal [Manual checked and confirm the the risk taker has generated loss for Company]",
            "Yes- Revenue Share Deal [Manual checked and confirm the the risk taker has generated profit for Company]",
            "The client has not had any previous relationship with Finalto",
        ],
        "required": False,
    },
]

load_dotenv(override=True)

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

app = Flask(__name__)


score_mapping = {
    "Contribute over $1m to Finalto": 5,
    "Contribute between $500k to $1m to Finalto": 3,
    "Contribute between $0 to $500k to Finalto": 1,
    "Making Finalto a loss between $0 to -$500k": 0,
    "Making Finalto a loss between -$500k to -$1m": 0,
    "Making Finalto a loss over $1m": 0,
    "Any one of the C-board members has disciplinary record, bankruptcy record": 0,
    "Any one of the C-board members is/was a board member of listed company": 3,
    "CEO,COO both are/were a board member of listed company": 5,
    "Market Maker / Principal": 1,
    "Hybrid (A-book + B-book)": 3,
    "Pure STP / Agency": 5,
    "Yes- Revenue Share Deal [Manual checked and confirm the the risk taker has generated loss for Company]": 0,
    "Yes- Revenue Share Deal [Manual checked and confirm the the risk taker has generated profit for Company]": 5,
    "No reliable public record found": 0,
    "Client does not hold any required regulatory license": 0,
    "The client has not had any previous relationship with Finalto": 0,
    "Others": 0,
}


def run_databricks_query(sql_query, params=[], get_pandas=False):
    """
    Executes a SQL query on Databricks and returns the results.
    Make sure your environment variables are set!
    """
    # The context manager handles opening and closing the connection
    server_hostname = os.getenv("DATABRICKS_HOST")
    http_path = os.getenv("DATABRICKS_HTTP_PATH")
    access_token = os.getenv("MY_TOKEN")

    with sql.connect(
        server_hostname=server_hostname, http_path=http_path, access_token=access_token
    ) as connection:
        with connection.cursor() as cursor:

            cursor.execute(sql_query, parameters=params)
            if get_pandas:
                return cursor.fetchall_arrow().to_pandas()
            else:
                # 1. Grab the column names from the cursor description
                if not cursor.description:
                    print(f"No results returned for query: {sql_query}", flush=True)
                    return []
                columns = [column[0] for column in cursor.description]

                # 2. Fetch the raw data (which comes back as a list of tuples)
                rows = cursor.fetchall()
                if len(rows) == 0:
                    print(f"No results found for query: {sql_query}", flush=True)
                    return []

                # 3. Use list comprehension to zip columns and rows into dictionaries
                dict_results = [dict(zip(columns, row)) for row in rows]
                return dict_results


@app.route("/", methods=["GET"])
def index():
    query = "SELECT * from live_mart.riskmkt_apac.revshare_form where status like 'Pass%' order by submitDate desc;"

    results = run_databricks_query(query)

    return render_template("index.html", data=results)


@app.errorhandler(500)
@app.errorhandler(404)
def handle_error(e):
    return render_template("error_page.html", message=str(e)), 500


@app.route("/internal-form", methods=["POST"])
def internal_form():
    raw_selected_data = request.form.get("selected_data")
    if not raw_selected_data:
        return "<h1>Error</h1> <p>External response data not found.</p>"

    selected_data = json.loads(raw_selected_data)

    status = selected_data["status"]
    disable_edit = False
    if status != enable_edit_status:
        disable_edit = True

    ignore_secondary_sales = (
        True
        if selected_data[secondary_sales_question] == secondary_sales_ignore_answer
        else False
    )
    actual_internal_form_questions = []
    for i_q in internal_form_questions:
        if ignore_secondary_sales and i_q["label"] == internal_secondary_sales_question:
            continue
        actual_internal_form_questions.append(i_q)

    selected_internal_form_value = {
        internal_question["label"]: None
        for internal_question in internal_form_questions
    }

    for q, a in selected_data.items():
        if q in selected_internal_form_value.keys() and a != "":
            selected_internal_form_value[q] = a

    external_form_data = []
    for q in question_ordered:
        external_form_data.append({"question": q, "answer": selected_data[q]})

    if selected_data:
        selected_response_id = selected_data["response_id"]
        total_score = selected_data["total_score"]
        return render_template(
            "internal_form_page.html",
            selected_response_id=selected_response_id,
            total_score=total_score,
            disable_edit=disable_edit,
            internal_form_questions=actual_internal_form_questions,
            selected_internal_form_value=selected_internal_form_value,
            external_form_data=external_form_data,
        )
    else:
        return "<h1>Error</h1> <p>No ID was selected.</p>"


@app.route("/review-form", methods=["POST"])
def review_form():
    data = dict(request.form)
    available_status = base_available_status

    status = data["status"]
    if status.startswith("Passed (1B)"):
        available_status = offerings_available_status
    elif status.startswith("Passed (2A)"):
        available_status = post_offerings_available_status

    if not data:
        return "<h1>Error</h1> <p>No data submitted.</p>"
    internal_score = 0
    double_score = False if data.get(internal_secondary_sales_question) else True
    for key, value in data.items():
        if key in [
            "selected_response_id",
            "external_score",
            "internal_score",
            "total_score",
        ]:
            continue
        if key == internal_primary_sales_question:
            score = int(score_mapping.get(value, 0))
            if double_score:
                score = score * 2
        else:
            score = int(score_mapping.get(value, 0))
        print(f"{key}: {score}")
        internal_score += score

    mapped_data = []
    data["internal_score"] = str(internal_score)
    data["total_score"] = str(int(data["external_score"]) + internal_score)
    for k, v in data.items():
        mapped_data.append({"question": k, "answer": v})

    return render_template(
        "review_page.html",
        form_data=mapped_data,
        available_status=available_status,
    )


@app.route("/submit", methods=["POST"])
def submit():
    set_str_list = []
    param_list = []
    data = dict(request.form)

    if not data:
        return render_template("error_page.html", message="No data submitted.")

    for key, value in data.items():
        if key in question_ordered + [
            "selected_status",
            "internal_score",
            "total_score",
        ]:
            continue
        set_str_list.append(f"`{key}` = ?")
        param_list.append(value)

    set_str = ", ".join(set_str_list)
    try:
        response_id = int(data["response_id"])
        internal_score = int(data["internal_score"])
        total_score = int(data["total_score"])
        status = data["selected_status"]
    except Exception as e:
        return render_template("error_page.html", message=f"Invalid input: {str(e)}")
    query = f"""
        UPDATE live_mart.riskmkt_apac.revshare_form
        SET 
            {set_str},
            internal_score = ?,
            total_score = ?,
            status = ?
        WHERE response_id = ?;
    """

    print(f"Query: {query}", flush=True)
    print(f"Params: {param_list + [internal_score, total_score, status, response_id]}")
    run_databricks_query(
        query, params=param_list + [internal_score, total_score, status, response_id]
    )

    return render_template("success_page.html")


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", 8000))

    app.run(debug=True, host=host, port=port, use_reloader=False)
    print(f"Flask app running on http://{host}:{port}")

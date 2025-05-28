from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models.models import Notebook, CellExecution, CellClickEvent
from app.utils.utils import get_time_boundaries, hash_user_id_with_salt
from app.utils.TSED import Calculate
from app.utils.llm import analyze_error_cell
from sqlalchemy import func, and_
from collections import Counter
import statistics
import datetime
import json
import requests

dashboard_bp = Blueprint('student_dashboard', __name__)

def validate_user_id(user_id):
    """Validate and hash user ID."""
    if not user_id:
        return None, jsonify({"error": "User ID is required"}), 400
    return hash_user_id_with_salt(user_id), None

### Get your error types distribution ###
@dashboard_bp.route('/<user_id>/errors/distrib', methods=['GET'])
def getUserErrorsDistribution(user_id):
    try:
        hashed_user_id, err = validate_user_id(user_id)
        if err:
            return err
        
        notebook_id = request.args.get('notebook_id')
        t_start, t_end = get_time_boundaries(request.args)

        query = db.session.query(
                CellExecution.error_type,
            ).filter(
                CellExecution.cell_type == 'CodeExecution',
                CellExecution.status == "error",
                CellExecution.user_id == hashed_user_id,
                (CellExecution.notebook_id == notebook_id) if notebook_id else True,
                and_(
                    CellExecution.t_finish > t_start if t_start else True,
                    CellExecution.t_finish <= t_end if t_end else True
                ),
            )
        
        error_types = [et[0] for et in query if et[0]]
        counter = Counter(error_types)
        return jsonify(dict(counter))
    
    except Exception as e:
        return jsonify({"error": "Failed to retrieve error distribution"}), 500

### Get your error types distribution timeline ###
@dashboard_bp.route('/<user_id>/errors/distrib/timeline', methods=['GET'])
def getUserErrorsDistributionTimeline(user_id):
    try:
        hashed_user_id, err = validate_user_id(user_id)
        if err:
            return err

        notebook_id = request.args.get('notebook_id')
        t_start, t_end = get_time_boundaries(request.args)

        query = db.session.query(
                func.array_agg(CellExecution.error_type),
                func.date(CellExecution.t_finish),
            ).filter(
                CellExecution.cell_type == 'CodeExecution',
                CellExecution.status == "error",
                CellExecution.user_id == hashed_user_id,
                (CellExecution.notebook_id == notebook_id) if notebook_id else True,
                and_(
                    CellExecution.t_finish > t_start if t_start else True,
                    CellExecution.t_finish <= t_end if t_end else True
                )
            ).group_by(
                func.date(CellExecution.t_finish)
            ).order_by(
                func.date(CellExecution.t_finish)
            )
        
        result = {
            date.isoformat(): dict(Counter(error_types))
            for error_types, date in query if error_types
        }
        return jsonify(result)
    
    except Exception:
        return jsonify({"error": "Failed to retrieve error timeline"}), 500

### Get your execs analysis, based on filters ###
@dashboard_bp.route('/<user_id>/execs/analysis', methods=['POST'])
def getUserExecsAnalysis(user_id):
    try:
        hashed_user_id, err = validate_user_id(user_id)
        if err:
            return err
        
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        data = request.get_json() or {}
        filters = data.get('filters', {})
        if not isinstance(filters, dict):
            return jsonify({"error": "Filters must be a dictionary"}), 400

        sort_by = data.get('sortBy', 'timeDesc')
        match sort_by:
            case 'errorType':
                sort_condition = CellExecution.error_type.asc()
            case 'timeAsc' :
                sort_condition = CellExecution.id.asc()
            case _:
                sort_condition = CellExecution.id.desc()

        if 'search' in filters:
            # Can't filter before search using flask-msearch...
            subq = CellExecution.query.msearch(
                filters['search']
            ).filter(
                CellExecution.cell_type == 'CodeExecution',
                CellExecution.user_id == hashed_user_id,
            )
        else:
            subq = CellExecution.query.filter(
                CellExecution.cell_type == 'CodeExecution',
                CellExecution.user_id == hashed_user_id,
            )

        for f_name, f_value in filters.items():
            match f_name:
                case 't1':
                    t1 = datetime.datetime.fromisoformat(f_value[:-1])
                    subq = subq.filter(
                        CellExecution.t_start > t1
                    )
                case 't2':
                    t2 = datetime.datetime.fromisoformat(f_value[:-1]) 
                    subq = subq.filter(
                        CellExecution.t_start <= t2
                    )
                case 'error_type':
                    subq = subq.filter(
                        CellExecution.error_type == f_value
                    )
                case 'status':
                    subq = subq.filter(
                        CellExecution.status == f_value
                    )
                case 'notebook_names':
                    notebook_ids = db.session.query(Notebook.notebook_id).filter(Notebook.name.in_(f_value)).all()
                    notebook_ids_list = [id[0] for id in notebook_ids]
                    subq = subq.filter(CellExecution.notebook_id.in_(notebook_ids_list))

        query = subq.order_by(sort_condition).limit(limit).offset(offset)
        
        result = [
            {
            'cell_input': res.cell_input,
            'cell_output_model': res.cell_output_model,
            'date': res.t_finish,
            } 
        for res in query]
        return jsonify(result)
    
    except ValueError as e:
        return jsonify({"error": f"Invalid input format: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": "Failed to retrieve execution analysis"}), 500

### Get your execution timeline ###
@dashboard_bp.route('/<user_id>/execs/timeline', methods=['GET'])
def getUserExecsTimeline(user_id):
    try:
        hashed_user_id, err = validate_user_id(user_id)
        if err:
            return err

        notebook_id = request.args.get('notebook_id')
        t_start, t_end = get_time_boundaries(request.args)

        query = db.session.query(
                func.count().label('execution_count'),
                func.date(CellExecution.t_finish).label('exec_date'),
            ).filter(
                CellExecution.cell_type == 'CodeExecution',
                CellExecution.user_id == hashed_user_id,
                (CellExecution.notebook_id == notebook_id) if notebook_id else True,
                and_(
                    CellExecution.t_finish > t_start if t_start else True,
                    CellExecution.t_finish <= t_end if t_end else True
                )
            ).group_by(
                func.date(CellExecution.t_finish)
            ).order_by(
                func.date(CellExecution.t_finish)
            )
        
        result = {
            row.exec_date.isoformat(): row.execution_count 
            for row in query
        }
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": "Failed to retrieve execution timeline"}), 500
    
@dashboard_bp.route('/<user_id>/comparison/time-spent/<notebook_id>', methods=['GET'])
def compareTimeSpent(user_id, notebook_id):
    try:
        hashed_user_id, err = validate_user_id(user_id)
        if err:
            return err
        
        t_start, t_end = get_time_boundaries(request.args)
        cell_id = request.args.get('cell_id')

        # subquery to average cell focus duration per user 
        query = db.session.query(
            CellClickEvent.user_id,
            func.array_agg(CellClickEvent.click_duration),
        ).filter(
            CellClickEvent.notebook_id == notebook_id,
            CellClickEvent.cell_id == cell_id if cell_id else True,
            and_(
                CellClickEvent.time > t_start if t_start else True,
                CellClickEvent.time <= t_end if t_end else True
            ),
            CellClickEvent.click_type == 'OFF',
            CellClickEvent.click_duration.isnot(None),
            CellClickEvent.click_duration <= 5000  # durations longer than this can be considered outliers
        ).group_by(
            CellClickEvent.user_id
        )

        res_dict = dict(query.all()) # user -> CellClickEvent.click_duration
        all_durations = [sum(durations) for durations in res_dict.values()]

        result = {
            'time': sum(res_dict[hashed_user_id]) if hashed_user_id in res_dict else None,
            'average': statistics.mean(all_durations) if all_durations else None,
            'min': min(all_durations) if all_durations else None,
            'max': max(all_durations) if all_durations else None,
            'median': statistics.median(all_durations) if all_durations else None,
            'all': all_durations,
        }

        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": "Failed to compare time spent"}), 500
    
@dashboard_bp.route('/<user_id>/comparison/similarity/<notebook_id>/<cell_id>', methods=['POST'])
def computeSimilarityHistogram(user_id, notebook_id, cell_id):    
    try:
        hashed_user_id, err = validate_user_id(user_id)
        if err:
            return err
        
        data = request.get_json()
        code = data.get('code')
        if not (code):
            return jsonify({"error": "Code field is required"}), 400
 
        # Subquery to get the max id for each user
        subq = db.session.query(
            CellExecution.user_id,
            func.max(CellExecution.id).label('max_id')
        ).filter(
            CellExecution.notebook_id == notebook_id,
            CellExecution.cell_id == cell_id if cell_id is not None else True,
            CellExecution.cell_type == 'CodeExecution',
        ).group_by(
            CellExecution.user_id
        ).subquery()

        # Main query to get the records for those max ids
        execs_query = db.session.query(CellExecution).join(
            subq,
            and_(
                CellExecution.user_id == subq.c.user_id,
                CellExecution.id == subq.c.max_id
            )
        )

        # Calculate scores and separate current user from others
        your_score = None
        your_code = None
        other_scores = []

        for exec in execs_query:
            score = Calculate(code, exec.cell_input, 1.0, 0.8, 1.0) # Weights as suggested by the paper   
            if exec.user_id == hashed_user_id:
                your_score = score
                your_code = exec.cell_input
            else:
                other_scores.append(score)

        # If current user not found in results, error
        if your_score is None or your_code is None:
            return jsonify({"error": "No execution found for you"}), 404
        
        return jsonify({
            'your_score': your_score,
            'your_code': your_code,
            'other_scores': other_scores,
        })

    except Exception as e:
        return jsonify({"error": "Failed to compute similarity"}), 500


### Computes similarity between two code snippets ###
@dashboard_bp.route('/similarity', methods=['POST'])
def computeSimilarity():    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        code1 = data.get('code1')
        code2 = data.get('code2')
        if not (code1 and code2):
            return jsonify({"error": "code1 and code2 fields are required"}), 400
        
        ts_score = Calculate(code1, code2, 1.0, 0.8, 1.0) # Weights as suggested by the paper        
        return jsonify(ts_score)

    except Exception as e:
        return jsonify({"error": "failed to process the code snippets"}), 500

### Explain errors using LLM ###
def validate_llm_config():
    """Check if LLM config is set."""
    if not all(
        current_app.config.get(key) 
        for key in ['LLM_API_URL', 'LLM_API_KEY', 'LLM_MODEL']
    ):
        return jsonify({"error": "LLM service is not configured."}), 503
    return None

@dashboard_bp.route('/explain', methods=['POST'])
def codeExplain():
    config_error = validate_llm_config()
    if config_error:
        return config_error

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided."}), 400

        # Validate required fields
        cell_input = data.get('cell_input')
        cell_output_model = data.get('cell_output_model')
        if not cell_input:
            return jsonify({"error": "cell_input is required."}), 400
        if not cell_output_model:
            return jsonify({"error": "cell_output_model is required."}), 400
        
        # Extract traceback
        traceback = None
        if isinstance(cell_output_model, list) and cell_output_model:
            traceback = cell_output_model[0].get('traceback')
        elif isinstance(cell_output_model, dict):
            traceback = cell_output_model.get('traceback')
        if not traceback:
            return jsonify({"error": "traceback in cell_output_model is required."}), 400
        
        # Normalize traceback to a string
        if isinstance(traceback, list):
            traceback = '\n'.join(traceback)
        elif not isinstance(traceback, str):
            return jsonify({"error": "traceback must be a string or list of strings."}), 400

        llm_answer = analyze_error_cell(
            api_url=current_app.config['LLM_API_URL'],
            model=current_app.config['LLM_MODEL'],
            api_key=current_app.config['LLM_API_KEY'],
            code_input=cell_input,
            traceback=traceback,
        )
        
        return jsonify(llm_answer)

    except json.JSONDecodeError as e:
        return jsonify({
            "error": "The AI service returned an invalid response. Please try again.",
            "details": str(e)
        }), 502

    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": "Failed to communicate with the AI service. Please try again.",
            "details": str(e)
        }), 502
    
    except Exception:
        return jsonify({"error": "An internal server error occurred."}), 500
        


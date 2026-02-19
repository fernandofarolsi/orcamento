from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database import get_db, log_audit

bp = Blueprint('tiers', __name__)

@bp.route('/api/tiers', methods=['GET'])
@jwt_required()
def api_tiers_list():
    db = get_db()
    tiers = db.execute('SELECT * FROM budget_tiers ORDER BY order_index').fetchall()
    return jsonify([dict(t) for t in tiers])

@bp.route('/api/tiers/<int:id>/rules', methods=['GET'])
@jwt_required()
def api_tier_rules(id):
    db = get_db()
    # Join with estoque to get item names if item_id is set
    query = '''
        SELECT tr.*, e.nome as item_nome 
        FROM tier_rules tr
        LEFT JOIN estoque e ON tr.item_id = e.id
        WHERE tr.tier_id = ?
    '''
    rules = db.execute(query, (id,)).fetchall()
    return jsonify([dict(r) for r in rules])

@bp.route('/api/tiers/<int:id>/rules', methods=['POST'])
@jwt_required()
def api_tier_rules_add(id):
    user_id = get_jwt_identity()
    data = request.json
    category = data.get('category')
    item_id = data.get('item_id')
    price_modifier = data.get('price_modifier', 1.0)
    
    if not category:
        return jsonify({'error': 'Category required'}), 400
        
    db = get_db()
    try:
        db.execute('''
            INSERT INTO tier_rules (tier_id, category, item_id, price_modifier)
            VALUES (?, ?, ?, ?)
        ''', (id, category, item_id, price_modifier))
        db.commit()
        log_audit(user_id, 'TIER_RULE_ADD', f"Added rule for tier {id}, cat {category}")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/tiers/rules/<int:rule_id>', methods=['DELETE'])
@jwt_required()
def api_tier_rules_delete(rule_id):
    user_id = get_jwt_identity()
    db = get_db()
    db.execute('DELETE FROM tier_rules WHERE id = ?', (rule_id,))
    db.commit()
    log_audit(user_id, 'TIER_RULE_DELETE', f"Deleted rule {rule_id}")
    return jsonify({'success': True})

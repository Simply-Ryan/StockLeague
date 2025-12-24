"""
Item #10: Flask Routes for Member Limits
Endpoints for managing league member limits and waitlist
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, g
from members_limit_manager import MembersLimitManager


def create_members_limit_blueprint(db, limit_manager: MembersLimitManager):
    """
    Create Flask blueprint for member limit routes
    
    Args:
        db: Database connection
        limit_manager: MembersLimitManager instance
        
    Returns:
        Blueprint with member limit routes
    """
    limit_bp = Blueprint('members', __name__, url_prefix='/leagues')
    
    # ========== Admin Routes ==========
    
    @limit_bp.route('/<int:league_id>/settings/members', methods=['GET'])
    def member_settings(league_id):
        """Display member settings page (admin-only)"""
        try:
            user_id = g.get('user_id')
            if not user_id:
                return redirect(url_for('login'))
            
            # Verify admin
            cursor = db.get_connection().cursor()
            cursor.execute('''
                SELECT is_admin FROM league_members
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, user_id))
            
            member = cursor.fetchone()
            if not member or not member['is_admin']:
                return "Not authorized", 403
            
            # Get league
            league = db.get_league(league_id)
            
            # Get limit info
            limit_info = limit_manager.get_league_limit(league_id)
            
            # Get waitlist
            waitlist = limit_manager.get_waitlist(league_id)
            
            # Get history
            history = limit_manager.get_limit_history(league_id)
            
            return render_template(
                'member_settings.html',
                league=league,
                limit_info=limit_info,
                waitlist=waitlist,
                history=history
            )
        
        except Exception as e:
            return f"Error: {str(e)}", 500
    
    @limit_bp.route('/<int:league_id>/limit', methods=['GET'])
    def get_limit(league_id):
        """Get member limit info (JSON API)"""
        try:
            limit_info = limit_manager.get_league_limit(league_id)
            
            if not limit_info:
                return jsonify({
                    'success': False,
                    'error': 'League not found or limit not initialized'
                }), 404
            
            return jsonify({
                'success': True,
                'limit': limit_info
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @limit_bp.route('/<int:league_id>/limit/set', methods=['POST'])
    def set_limit(league_id):
        """Set member limit (admin-only)"""
        try:
            user_id = g.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'error': 'Not authenticated'}), 401
            
            # Get parameters
            max_members = request.json.get('max_members')
            reason = request.json.get('reason')
            
            if max_members is None:
                return jsonify({'success': False, 'error': 'max_members required'}), 400
            
            # Set limit
            success, message = limit_manager.set_member_limit(
                league_id=league_id,
                max_members=max_members,
                admin_id=user_id,
                reason=reason
            )
            
            if success:
                # Log action
                if hasattr(g, 'audit_logger'):
                    g.audit_logger.log_action(
                        action='UPDATE',
                        resource_type='LEAGUE_SETTINGS',
                        resource_id=league_id,
                        user_id=user_id,
                        details={'setting': 'member_limit', 'value': max_members},
                        ip_address=request.remote_addr
                    )
                
                return jsonify({
                    'success': True,
                    'message': message,
                    'limit': limit_manager.get_league_limit(league_id)
                })
            else:
                return jsonify({'success': False, 'error': message}), 400
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @limit_bp.route('/<int:league_id>/limit/enforce', methods=['POST'])
    def toggle_enforcement(league_id):
        """Enable/disable limit enforcement (admin-only)"""
        try:
            user_id = g.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'error': 'Not authenticated'}), 401
            
            enforce = request.json.get('enforce', True)
            
            success, message = limit_manager.enforce_limit(league_id, enforce)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': message
                })
            else:
                return jsonify({'success': False, 'error': message}), 400
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ========== Waitlist Routes ==========
    
    @limit_bp.route('/<int:league_id>/waitlist', methods=['GET'])
    def get_waitlist(league_id):
        """Get league waitlist (admin-only)"""
        try:
            user_id = g.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'error': 'Not authenticated'}), 401
            
            # Verify admin
            cursor = db.get_connection().cursor()
            cursor.execute('''
                SELECT is_admin FROM league_members
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, user_id))
            
            member = cursor.fetchone()
            if not member or not member['is_admin']:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403
            
            waitlist = limit_manager.get_waitlist(league_id)
            
            return jsonify({
                'success': True,
                'league_id': league_id,
                'waitlist': waitlist,
                'count': len(waitlist)
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @limit_bp.route('/<int:league_id>/waitlist/promote/<int:user_id>', methods=['POST'])
    def promote_from_waitlist(league_id, user_id):
        """Manually promote user from waitlist (admin-only)"""
        try:
            admin_id = g.get('user_id')
            if not admin_id:
                return jsonify({'success': False, 'error': 'Not authenticated'}), 401
            
            # Verify admin
            cursor = db.get_connection().cursor()
            cursor.execute('''
                SELECT is_admin FROM league_members
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, admin_id))
            
            member = cursor.fetchone()
            if not member or not member['is_admin']:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403
            
            # Try to add member
            success, message = limit_manager.add_member(league_id, user_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'User promoted from waitlist and added to league',
                    'limit': limit_manager.get_league_limit(league_id)
                })
            else:
                return jsonify({'success': False, 'error': message}), 400
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @limit_bp.route('/<int:league_id>/waitlist/<int:user_id>', methods=['DELETE'])
    def remove_from_waitlist(league_id, user_id):
        """Remove user from waitlist"""
        try:
            admin_id = g.get('user_id')
            if not admin_id:
                return jsonify({'success': False, 'error': 'Not authenticated'}), 401
            
            # Allow self-removal or admin removal
            if admin_id != user_id:
                cursor = db.get_connection().cursor()
                cursor.execute('''
                    SELECT is_admin FROM league_members
                    WHERE league_id = ? AND user_id = ?
                ''', (league_id, admin_id))
                
                member = cursor.fetchone()
                if not member or not member['is_admin']:
                    return jsonify({'success': False, 'error': 'Not authorized'}), 403
            
            success, message = limit_manager.remove_from_waitlist(league_id, user_id)
            
            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'error': message}), 400
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ========== Info Routes ==========
    
    @limit_bp.route('/<int:league_id>/member-count', methods=['GET'])
    def member_count(league_id):
        """Get league member count"""
        try:
            count = limit_manager.get_member_count(league_id)
            limit_info = limit_manager.get_league_limit(league_id)
            
            return jsonify({
                'success': True,
                'league_id': league_id,
                'current_members': count,
                'limit': limit_info['max_members'] if limit_info else None,
                'is_full': limit_info['is_full'] if limit_info else None
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @limit_bp.route('/<int:league_id>/can-join', methods=['GET'])
    def can_join(league_id):
        """Check if league can accept new members"""
        try:
            can_add, message = limit_manager.can_add_member(league_id)
            limit_info = limit_manager.get_league_limit(league_id)
            
            return jsonify({
                'success': True,
                'league_id': league_id,
                'can_join': can_add,
                'message': message,
                'limit_info': limit_info
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @limit_bp.route('/<int:league_id>/limit-history', methods=['GET'])
    def limit_history(league_id):
        """Get member limit change history (admin-only)"""
        try:
            user_id = g.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'error': 'Not authenticated'}), 401
            
            # Verify admin
            cursor = db.get_connection().cursor()
            cursor.execute('''
                SELECT is_admin FROM league_members
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, user_id))
            
            member = cursor.fetchone()
            if not member or not member['is_admin']:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403
            
            history = limit_manager.get_limit_history(league_id)
            
            return jsonify({
                'success': True,
                'league_id': league_id,
                'history': history
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return limit_bp

"""
Item #9: Flask Routes for Invite Code Management
Endpoints for creating, validating, and managing invite codes
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, g
from datetime import datetime
from invite_manager import InviteCodeManager


def create_invite_blueprint(db, invite_manager: InviteCodeManager):
    """
    Create Flask blueprint for invite code routes
    
    Args:
        db: Database connection
        invite_manager: InviteCodeManager instance
        
    Returns:
        Blueprint with invite routes
    """
    invite_bp = Blueprint('invite', __name__, url_prefix='/invite')
    
    # ========== Admin Routes (League Management) ==========
    
    @invite_bp.route('/create/<int:league_id>', methods=['POST'])
    def create_code(league_id):
        """Create a new invite code (admin-only)"""
        try:
            # Get current user
            user_id = g.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'error': 'Not authenticated'}), 401
            
            # Get parameters
            expiration_days = request.json.get('expiration_days', 7)
            is_single_use = request.json.get('is_single_use', False)
            max_uses = request.json.get('max_uses')
            metadata = request.json.get('metadata')
            
            # Create code
            success, code, message = invite_manager.create_invite_code(
                league_id=league_id,
                created_by=user_id,
                expiration_days=expiration_days,
                is_single_use=is_single_use,
                max_uses=max_uses,
                metadata=metadata
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'code': code,
                    'message': message,
                    'expires_at': (datetime.utcnow().timestamp() + (expiration_days * 86400))
                })
            else:
                return jsonify({'success': False, 'error': message}), 400
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @invite_bp.route('/<int:league_id>/codes', methods=['GET'])
    def list_codes(league_id):
        """List all active invite codes for a league (admin-only)"""
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
            
            # Get codes
            codes = invite_manager.get_league_codes(league_id, active_only=False)
            
            return jsonify({
                'success': True,
                'league_id': league_id,
                'codes': codes
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @invite_bp.route('/<int:league_id>/codes/html', methods=['GET'])
    def codes_page(league_id):
        """Display invite codes management page"""
        try:
            user_id = g.get('user_id')
            if not user_id:
                return redirect(url_for('login'))
            
            # Get league
            league = db.get_league(league_id)
            if not league:
                return "League not found", 404
            
            # Verify admin
            cursor = db.get_connection().cursor()
            cursor.execute('''
                SELECT is_admin FROM league_members
                WHERE league_id = ? AND user_id = ?
            ''', (league_id, user_id))
            
            member = cursor.fetchone()
            if not member or not member['is_admin']:
                return "Not authorized", 403
            
            # Get codes
            codes = invite_manager.get_league_codes(league_id, active_only=False)
            
            # Get analytics
            analytics = invite_manager.get_analytics(league_id)
            
            return render_template(
                'invite_codes.html',
                league=league,
                codes=codes,
                analytics=analytics
            )
        
        except Exception as e:
            return f"Error: {str(e)}", 500
    
    @invite_bp.route('/<int:league_id>/codes/<code>/users', methods=['GET'])
    def code_users(league_id, code):
        """Get users who used a code"""
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
            
            # Get users
            users = invite_manager.get_code_users(code)
            
            return jsonify({
                'success': True,
                'code': code,
                'users': users
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @invite_bp.route('/<int:league_id>/codes/<code>/deactivate', methods=['POST'])
    def deactivate_code(league_id, code):
        """Deactivate an invite code"""
        try:
            user_id = g.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'error': 'Not authenticated'}), 401
            
            success, message = invite_manager.deactivate_code(code, league_id, user_id)
            
            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'error': message}), 400
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ========== Public Routes (User Actions) ==========
    
    @invite_bp.route('/<code>', methods=['GET'])
    def validate_invite(code):
        """Validate an invite code and show join page"""
        try:
            is_valid, code_info, message = invite_manager.validate_code(code)
            
            if not is_valid:
                return render_template('invite_invalid.html', error=message), 404
            
            # Get league info
            league = db.get_league(code_info['league_id'])
            
            return render_template(
                'invite_join.html',
                code=code,
                league=league,
                code_info=code_info
            )
        
        except Exception as e:
            return render_template('invite_invalid.html', error=str(e)), 500
    
    @invite_bp.route('/<code>/join', methods=['POST'])
    def use_code(code):
        """Use an invite code to join a league"""
        try:
            user_id = g.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'error': 'Not authenticated'}), 401
            
            # Use code
            success, league_id, message = invite_manager.use_code(
                code=code,
                user_id=user_id,
                ip_address=request.remote_addr
            )
            
            if success:
                # Log the action
                if hasattr(g, 'audit_logger'):
                    g.audit_logger.log_action(
                        action='JOIN',
                        resource_type='LEAGUE',
                        resource_id=league_id,
                        user_id=user_id,
                        details={'via_invite_code': code},
                        ip_address=request.remote_addr
                    )
                
                return jsonify({
                    'success': True,
                    'league_id': league_id,
                    'message': message
                })
            else:
                return jsonify({'success': False, 'error': message}), 400
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @invite_bp.route('/<code>/validate', methods=['GET'])
    def validate_code_api(code):
        """API endpoint to validate a code (without joining)"""
        try:
            is_valid, code_info, message = invite_manager.validate_code(code)
            
            if is_valid:
                # Get league info
                league = db.get_league(code_info['league_id'])
                
                return jsonify({
                    'success': True,
                    'valid': True,
                    'code': code,
                    'league': {
                        'id': league['id'],
                        'name': league['name'],
                        'description': league.get('description'),
                        'member_count': db.get_league_member_count(league['id'])
                    },
                    'expires_at': code_info['expires_at'],
                    'uses_remaining': (code_info['max_uses'] - code_info['current_uses']) if code_info['max_uses'] else 'unlimited'
                })
            else:
                return jsonify({
                    'success': False,
                    'valid': False,
                    'error': message
                }), 400
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @invite_bp.route('/<code>/info', methods=['GET'])
    def code_info(code):
        """Get info about an invite code (public)"""
        try:
            is_valid, code_info, message = invite_manager.validate_code(code)
            
            if not is_valid:
                return jsonify({'success': False, 'error': message}), 404
            
            league = db.get_league(code_info['league_id'])
            
            # Calculate expiration
            from datetime import datetime
            expires_at = datetime.fromisoformat(code_info['expires_at'])
            days_left = (expires_at - datetime.utcnow()).days
            
            return jsonify({
                'success': True,
                'code': code,
                'league_name': league['name'],
                'expires_in_days': max(0, days_left),
                'uses_remaining': (code_info['max_uses'] - code_info['current_uses']) if code_info['max_uses'] else None
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ========== Admin Cleanup Routes ==========
    
    @invite_bp.route('/admin/cleanup', methods=['POST'])
    def cleanup_codes():
        """Clean up expired codes (admin-only)"""
        try:
            user_id = g.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'error': 'Not authenticated'}), 401
            
            # Verify super admin
            cursor = db.get_connection().cursor()
            cursor.execute('SELECT is_super_admin FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user or not user.get('is_super_admin'):
                return jsonify({'success': False, 'error': 'Super admin only'}), 403
            
            dry_run = request.json.get('dry_run', True)
            count = invite_manager.cleanup_expired_codes(dry_run=dry_run)
            
            return jsonify({
                'success': True,
                'count_cleaned': count,
                'dry_run': dry_run,
                'message': f'{"Would clean" if dry_run else "Cleaned"} {count} expired codes'
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return invite_bp

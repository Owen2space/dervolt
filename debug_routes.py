from flask import Flask

def add_debug_routes(app):
    @app.route('/debug')
    def debug_route():
        return "Debug route working correctly!", 200 
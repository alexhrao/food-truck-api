from flask import Flask
from flask_restful import Resource, Api
from google.cloud import storage, firestore
import base64

db = firestore.Client()

app = Flask(__name__)
api = Api(app)

class LiveView(Resource):
    def get(self, view):
        doc_ref = db.collection(u'last-view').document(view)
        last_view = doc_ref.get().to_dict()
        file_data = str(base64.b64encode(storage.Client().bucket(view).blob(last_view['filename']).download_as_string()), encoding='utf-8')
        return ({
            'data': file_data,
            'time': last_view['time_updated'].isoformat()
        })
        

api.add_resource(LiveView, '/api/views/<string:view>')

if __name__=='__main__':
    app.run(host='127.0.0.1', port=8080, debug=False)
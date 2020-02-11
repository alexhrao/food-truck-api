from flask import Flask
from flask_restful import Resource, Api
from google.cloud import storage, firestore
from flask_cors import CORS
import base64

db = firestore.Client()

app = Flask(__name__)
CORS(app)
api = Api(app)

class LiveView(Resource):
    def get(self, view):
        doc_ref = db.collection(u'last-view').document(view)
        last_view = doc_ref.get().to_dict()
        if last_view['filename'] is None or last_view['filename'] == '':
            return ({
                'data': '',
                'time': '',
            })
        file_data = str(base64.b64encode(storage.Client().bucket(view).blob(last_view['filename']).download_as_string()), encoding='utf-8')
        return ({
            'data': file_data,
            'time': last_view['time_updated'].isoformat()
        })

class Views(Resource):
    def get(self):
        docs = [{ 'id': d.id, 'display': d.get().to_dict()['display_name'] } for d in db.collection('last-view').list_documents()]
        print(docs)
        return docs


api.add_resource(LiveView, '/api/views/<string:view>')
api.add_resource(Views, '/api/views')

if __name__=='__main__':
    app.run(host='127.0.0.1', port=8080, debug=False)
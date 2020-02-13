from flask import Flask, Response
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

# Image Document output looks like this:
"""
{
    'key': 'filename',
    'bucket': 'bucket-name',
    'filename': 'filename.png',
    'valid': bool,
    'labels': [
        {
            'groupName': 'group-name',
            'groupType': 'single'|'multiple'|'numeric'
            'values': 'label-name'|['label-names']|number
        },
        {
            'groupName': 'group-name',
            'groupType': 'single'|'multiple'|'numeric'
            'values': 'label-name'|['label-names']|number
        },...
    ]
}
"""
class ImageDocument(Resource):
    def get(self, bucket_name='', image_name=''):
        if bucket_name == '':
            # No bucket - just get the first one that hasn't been seen!
            docs = list(db.collection_group('labels').where('seen', '==', False).limit(1).stream())
            if len(docs) == 0:
                return {}
            doc = docs[0]
            return self.get(doc.get('bucket'), doc.id)
        doc_ref = db.collection('images').document(bucket_name).collection('labels').document(image_name)
        doc = doc_ref.get()
        if not doc.exists:
            return {}
        out = {
            'key': image_name,
            'bucket': bucket_name,
            'filename': '{0}.png'.format(image_name),
            'valid': doc.get('valid'),
            'seen': doc.get('seen'),
            'labels': list()
        }
        for labelGroup in doc.get('labels'):
            label = labelGroup.get('group').get()
            out['labels'].append({
                'groupName': label.id,
                'groupType': label.get('groupType'),
                'values': labelGroup.get('values')
            })
        return out

@app.route('/api/snapshots/<string:bucket_name>/<string:image_name>')
def snapshot(bucket_name, image_name):
    file_ref = storage.Client().bucket(bucket_name).blob('{0}.png'.format(image_name))
    file_data = file_ref.download_as_string()
    resp = Response(file_data)
    resp.headers['Content-Type'] = file_ref.content_type
    return resp

api.add_resource(LiveView, '/api/views/<string:view>')
api.add_resource(Views, '/api/views')
api.add_resource(ImageDocument, '/api/images/<string:bucket_name>/<string:image_name>', '/api/images/')

if __name__=='__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
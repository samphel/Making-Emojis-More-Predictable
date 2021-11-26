import pickle
import numpy as np
import pandas as pd
from flask.helpers import flash
from sklearn.feature_extraction.text import TfidfVectorizer
import nltk
import preprocessor as p
import re
import string
from nltk import word_tokenize
from flask import Flask, render_template, request
from gensim import models
from collections import defaultdict



app = Flask(__name__)


class TfidfEmbeddingVectorizer(object):
    def __init__(self, model):
        self.model = model
        self.modelweight = None
        self.dim = 200
        # self.dim = len(model[model.keys()[0]])

    def fit(self, X):
        tfidf = TfidfVectorizer(analyzer=lambda x: x)
        tfidf.fit(X)
        # if a word was never seen - it must be at least as infrequent
        # as any of the known words - so the default idf is the max of 
        # known idf's
        max_idf = max(tfidf.idf_)
        self.modelweight = defaultdict(
		    lambda: max_idf,
		    [(w, tfidf.idf_[i]) for w, i in tfidf.vocabulary_.items()])

        return self

    def transform(self, X):
        return np.array([
		        np.mean([self.model[w] * self.modelweight[w]
		                 for w in words if w in self.model] or
		                [np.zeros(self.dim)], axis=0)
		        for words in X
		    ])

def word_embeddings(tweets, embedding):
    if embedding == "word2vec":
        X = word2vec(tweets)
        w2v = models.Word2Vec(X, vector_size=200, window=5, sg=0,min_count=1)
        model = dict(zip(w2v.wv.index_to_key, w2v.wv.vectors))
        
    elif embedding == "glove":
        with open("./src/glove.twitter.27B.200d.txt", "rb") as lines:
            model = {line.split()[0]: np.array(map(float, line.split()[1:]))
                for line in lines}


    vec = TfidfEmbeddingVectorizer(model)
    vec.fit(tweets)
    matrix = vec.transform(tweets)

    return matrix

def word2vec(tweets):
    texts = []

    for tweet in tweets:
        texts.append(tweet.split())

    return texts


stopword = nltk.corpus.stopwords.words('english')
stopword += ['yr', 'year', 'woman', 'man', 'girl','boy','one', 'two', 'sixteen', 'yearold', 'fu', 'weeks', 'week',
            'treatment', 'associated', 'patients', 'may','day', 'case','old']
mapping = {0:'&#x2764',1:'&#x1F60D',2:'&#x1F602',3:'&#x1F495',4:'&#x1F525', 5:'&#x1F60A',6:'&#x1F60E',7:'&#x2728',8:'&#x1F499',9:'&#x1F618',10:'&#x1F4F7',11:'&#x1F1F8',12:'&#x2600',13:'&#x1F49C',14:'&#x1F609',15:'&#x1F4AF',16:'&#x1F601',17:'&#x1F384',18:'&#x1F4F8',19:'&#x1F61C'}
def clean_text(text):
    text = re.sub(r'@user','',text)
    text  = "".join([char.lower() for char in text if char not in string.punctuation])
    text  = "".join([char.lower() for char in text if char not in ['…','\n']])
    text = re.sub('[0-9]+', '', text)
    # text = ''.join(i for i in text if ord(i)<128)
    text = re.sub('\s+', ' ', text)
    text = word_tokenize(text)    
    for i in range(len(text)):
        word = text[i]
        newword = word[0]
        prev = word[0]
        prev_cnt = 0
        for j in range(1,len(word)):
            if word[j] == prev:
                prev_cnt+=1
                if prev_cnt < 2:
                    newword += word[j]
            else:
                newword += word[j]
                prev = word[j]
                prev_cnt = 0
                
        text[i] = newword

    text = [word for word in text if word not in stopword]
    #text = [str(TextBlob(word).correct()) for word in text]
    text = [word for word in text if word not in stopword]
    # text = [ps.stem(word) for word in text]
    # text = [word for word in text if 10>len(word)>2]
    # for word in text:
    #     if len(word)<=2:
    #         print(word)
    new_text = " ".join([word for word in text])
    return "tweet " + new_text

def addWE(text,embedding,bow_test):
    emb_text = word_embeddings([text], embedding)
    print("hello")
    new_text = np.concatenate((emb_text, bow_test), axis=1)
    return new_text

modelsList = {'AdaBoost':'finalModelAB','SVM+WE':'SVM_linear_0.3','SVM':'noWE_SVM_0.3'}

def get_prediction(text,mod):
    vec = pickle.load(open('./tfvec','rb'))
    p_processed = p.clean(text)
    finPre = clean_text(p_processed)
    bow_test =  vec.transform([finPre]).toarray()
    modelsPath = './src/finalModels/modelPickles/'
    if mod in ['SVM+WE']:
        bow_test = addWE(text,'word2vec',bow_test)
    elif mod in ['AdaBoost']:
        bow_test = addWE(text,'word2vec',bow_test)
    model = pickle.load(open(modelsPath+modelsList[mod],'rb'))
    prediction = model.predict(bow_test)

    return prediction



@app.route('/',methods = ['GET','POST'])
def hello_world():
    prediction = [0]
    models = modelsList.keys()
    if request.method == 'POST':
        model = request.form['models']
        prediction = get_prediction(request.form['tweet'],model)
    return render_template('index.html',prediction=mapping[prediction[0]],models=models)


if __name__ == '__main__':
      app.run(host='127.0.0.1', port=8000)
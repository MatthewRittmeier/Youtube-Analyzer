from googleapiclient.discovery import build
import os, shutil
import requests
import json

api_key = 'AIzaSyBNp4NetZmqY791wFPD2AvbhVP9Scs3rh8'
youtube = build('youtube', 'v3', developerKey=api_key)
imgFolder = 'Images/'
JSONFolder = 'JSON Data/'

def QueryUser():
    # Real code - Api request
    prompt = input("Enter search term to analyze. To do multiple for a better analysis, seperate each search term with a '|': ")
    maxResults = input("Maximum amount of returned videos (capped at 50): ")

    if maxResults == "" or int(maxResults) > 50:
        print('Returning 50 results')
        maxResults = "50"

    # Delete images first?
    if input("Clear previous analysis first? y/n?: ") == 'y':
        for filename in os.listdir(imgFolder):
            file_path = os.path.join(imgFolder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))
        for filename in os.listdir(JSONFolder):
            file_path = os.path.join(JSONFolder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))
                
    return (prompt, maxResults)

def DownloadYoutubeData(searchTerm, maxResults):
    # Make API request        
    request = youtube.search().list(
        q=searchTerm,
        part='id, snippet',
        maxResults=maxResults,
        type='video',
    )

    # Temp variables
    response = request.execute()
    videos = []
    
    # Save response data
    for search_result in response.get('items', []):
            
        # Save video data
        video_url = 'https://www.youtube.com/watch?v=' + search_result['id']['videoId']
        channel_url = 'https://www.youtube.com/channel/' + search_result['snippet']['channelId']
        image_url = search_result['snippet']['thumbnails']['high']['url']
        videos.append(search_result['id']['videoId'])
        
        # File dir
        file_dir = imgFolder + search_result['id']['videoId'] + '.jpeg'
        
        # Change image save location
        directory = os.path.dirname(file_dir)
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Save image file
        img_data = requests.get(image_url).content
        with open(file_dir, 'wb') as handler:
            handler.write(img_data)
            
        # Active console visualization
        print('Video Title: ' + search_result['snippet']['title'])
        print('Video URL: ' + video_url)
        print('Channel URL: ' + channel_url)

    # Seperate video ids into string split list
    promptString = ""
    for videoAtIdx in  videos:
        promptString = promptString + "," + videoAtIdx
    promptString = promptString[1:]

    # Request make
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=promptString,
    ).execute()

    # Create and save JSON data that will be used
    for search_result in request.get('items', []):    
        # File dir
        file_dir = JSONFolder + search_result['id'] + '.json'
        
        # Change Json save location
        directory = os.path.dirname(file_dir)
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Attempt to get tags (tags dont always return)
        try:
            tags = search_result['snippet']['tags'],
        except Exception:
            tags = []
            
        try:
            commentCount = int(search_result['statistics']['commentCount'])
        except Exception:
            commentCount = int(0)
            
        # Json format
        data = {
            "videoDetails":{
                "VideoLink": 'https://www.youtube.com/watch?v=' + search_result['id'],
                "ChannelLink": 'https://www.youtube.com/channel/' + search_result['snippet']['channelId'],
                "VideoId": search_result['id'],
                "ChannelId": search_result['snippet']['channelId'],
                "Title": search_result['snippet']['title'],
                "ChannelName": search_result['snippet']['channelTitle'],
                "Description": search_result['snippet']['description'],
            },
            
            "stats":{
                "ViewCount": search_result['statistics']['viewCount'],
                "LikeCount": search_result['statistics']['likeCount'],
                "CommentCount": commentCount,
                "Like2ViewRatio": int(search_result['statistics']['likeCount']) / int(search_result['statistics']['viewCount']),
                "Comment2ViewRatio": commentCount / int(search_result['statistics']['viewCount']),
                "Tags": tags,
            }
        }
        
        print(data)
        
        # Save file
        save_file = open(file_dir, "w")  
        json.dump(data, save_file, indent = 6)  
        save_file.close()   
        print(promptString)
        
    # Close
    youtube.close()

def AnalyzeYoutubeData():
    # Setup variables
    Words = []
    WordCounts = []
    
    for dir, sub, files in os.walk(JSONFolder):
        for data in files:
            
            # Load data for processing
            print(data)
            data = json.load(open(dir + data))
            
            # Slice title into a list of words
            list = str(data['videoDetails']['Title']).split()
            # Analyze terms used in the titles
            for word in list:
                if word not in Words:
                    Words.append(word)
                    WordCounts.append(1)
                else:
                    index = Words.index(word)
                    WordCounts[index] = WordCounts[index] + 1
            print(Words)
            print(WordCounts)
            
    Words = [x for _, x in sorted(zip(WordCounts, Words))]
    WordCounts.sort()
    Words.reverse()
    WordCounts.reverse()
    
    print(Words)
    print(WordCounts)

# Main
if __name__ == "__main__":
    prompt, maxResults = QueryUser()
    list = prompt.split('|')
    
    for searchTerm in list:
        DownloadYoutubeData(searchTerm, maxResults)
        
    AnalyzeYoutubeData()
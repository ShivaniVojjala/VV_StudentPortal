    blob_client = blob_service_client.get_blob_client(container = container, blob = filename)
         
#             with open  (filename,"rb")  as data:
#                 try:
#                     blob_client.upload_blob(data, overwrite=True)
#                     msg = "Upload Done ! "
#                 except:
#                     pass
#             os.remove(filename)
            
#             # os.remove(filename1)
#     return render_template("dashboard.html", msg='uploaded' )
# # # upload('filename')




# # dashboard1
# @app.route('/dashboard', methods=['GET','POST'])
# # @login_required
from django_prose_editor.fields import create_sanitizer
EXTENSIONS = {'Bold':True,'Italic':True,'Heading':{'levels':[2,3]},'BulletList':True,'OrderedList':True,'ListItem':True,'Blockquote':True,'Link':{'protocols':['http','https','mailto']},'HardBreak':True}
sanitize_html = create_sanitizer(EXTENSIONS)

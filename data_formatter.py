import sublime
import sublime_plugin

from .util import communicate, data_type_recognition


class DataFormatterCommand(sublime_plugin.TextCommand):
    def init_processed_region(self):
        selection = self.view.sel()[0]
        self.selection = selection
        self.processed_region = sublime.Region(0, self.view.size())
        if selection.empty():
            self.selection = None
            return
        self.processed_region = selection.intersection(self.processed_region)

    def get_code(self):
        return self.view.substr(self.processed_region)

    def update_code(self, edit, code):
        self.view.replace(edit, self.processed_region, code)

        new_selection = self.view.sel()[0]
        if new_selection:
            # Inserting \n if selection ends in the middle of the line
            end_point = new_selection.end()
            _, end_column = self.view.rowcol(end_point + 1)
            if end_column > 0:
                self.view.insert(edit, new_selection.end(), '\n')

            # Inserting \n if selection starts in the middle of the line
            begin_point = new_selection.begin()
            _, begin_column = self.view.rowcol(begin_point)
            if begin_column > 0:
                self.view.insert(edit, begin_point, '\n')

    def error(self, error_message):
        sublime.error_message(error_message)

    def run(self, edit):
        self.init_processed_region()
        try:
            formatted_code = self.format_code(self.get_code())
        except Exception as e:
            self.error(str(e))
        else:
            self.update_code(edit, formatted_code)


class DataFormatterJsonCommand(DataFormatterCommand):
    def format_code(self, code):
        import os.path

        format_json_script = os.path.join(os.path.dirname(__file__), 'format_json.js')
        try:
            s = sublime.load_settings("Data Formatter.sublime-settings")
            nodejs_path = s.get('nodejs_path', '/usr/local/bin/node')
            return communicate((nodejs_path, format_json_script), code).strip()
        except Exception as e:
            raise Exception('JSON Formatter: ' + str(e))


class DataFormatterXmlCommand(DataFormatterCommand):
    def format_code(self, code):
        import xml.dom.minidom
        import re

        XML_DECLARATION = re.compile(r'^(<\?xml[^>]+>)')

        # We cut off xml declaration to add it in the end
        xml_declaration = XML_DECLARATION.match(code)
        if xml_declaration:
            xml_declaration = xml_declaration.groups()[0]
            xml_declaration = xml_declaration.strip() + '\n'
            code = XML_DECLARATION.sub('', code)
        else:
            xml_declaration = ''

        try:
            xml = xml.dom.minidom.parseString(code)
            formatted = xml.toprettyxml()
        except Exception as e:
            raise Exception('XML Formatter: ' + str(e))

        # minidom in some cases inserts empty lines in formatted file, so we're getting rid of them
        formatted_lines = [line for line in formatted.splitlines() if line.strip()]
        formatted = '\n'.join(formatted_lines)

        # prettyfied xml always has exta added xml declaration on the top
        # we remove it to have more control over it
        formatted = XML_DECLARATION.sub('', formatted)

        return xml_declaration + formatted.strip()


class DataFormatterFormatCommand(DataFormatterJsonCommand, DataFormatterXmlCommand):
    def format_code(self, code):
        data_type = data_type_recognition(code)
        use_explicit_disclaimer = '\n\nIf data type wasn\'t recognised correctly use explicit formatter.'
        if data_type == 'xml':
            try:
                return DataFormatterXmlCommand.format_code(self, code)
            except Exception as e:
                raise Exception(str(e) + use_explicit_disclaimer)
        elif data_type == 'json':
            try:
                return DataFormatterJsonCommand.format_code(self, code)
            except Exception as e:
                raise Exception(str(e) + use_explicit_disclaimer)
        else:
            raise Exception('Not recognised data type. Try to use explicit formatter.')

import os
import os.path
import errno
from collections import namedtuple
from datetime import datetime

from filecommand import FileCommand


Rule = namedtuple('Rule', ['after_date', 'before_date', 'format'])


class OrganizeCommand(FileCommand):

    DATE_FORMATS = ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S']

    def __init__(self, config_path):
        super(OrganizeCommand, self).__init__()
        import json
        with open(config_path, 'r') as f:
            self._config = json.loads(f.read())
        self._default_format = self._config['format']
        self._rules = self._load_rules()

    def _load_rules(self):
        def parse_date(str):
            dt = None
            for fmt in OrganizeCommand.DATE_FORMATS:
                try:
                    dt = datetime.strptime(str, fmt)
                except:
                    pass
            if dt is None:
                raise ValueError("Invalid date '%s'. Valid formats: %s"
                                 % (str, OrganizeCommand.DATE_FORMATS))
            return dt

        rules = []
        for r in self._config['rules']:
            after_date = parse_date(r['after_date'])
            before_date = parse_date(r['before_date'])
            rule = Rule(after_date=after_date, before_date=before_date,
                        format=r['format'])
            # print rule.after_date, rule.before_date
            rules.append(rule)

        rules = sorted(rules,
                       lambda r1, r2: r1.after_date < r2.after_date)
        prev_rule = None
        for rule in rules:
            if prev_rule and rule.after_date < prev_rule.before_date:
                raise ValueError("Rule dates may not overlap")
        return rules

    def process_file(self, input_path, output_dir):
        fmt_klass = self._get_metadata_handler(input_path)
        with fmt_klass(input_path) as file_fmt:
            creation_date = file_fmt.creation_date
        rule = self._get_matching_rule(creation_date)
        if rule:
            org_format = rule.format % {'default': self._default_format}
        else:
            org_format = self._default_format

        metadata = {}
        directives = ('Y', 'm', 'B', 'H', 'M', 'S')
        for d in directives:
            metadata[d] = datetime.strftime(creation_date, '%' + d)
        org_dir = org_format % metadata

        _, filename = os.path.split(input_path)
        output_dir = os.path.join(output_dir, org_dir)
        mkdir_p(output_dir)
        output_path = os.path.join(output_dir, filename)

        import shutil
        shutil.copy2(input_path, output_path)
        print '%s -> %s' % (input_path, output_path)

    def _get_matching_rule(self, file_date):
        for rule in self._rules:
            # print file_date, rule.after_date, rule.before_date
            if file_date >= rule.after_date and \
                    file_date < rule.before_date:
                return rule
        return None


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
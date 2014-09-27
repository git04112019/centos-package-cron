import os
import sys
import yum
import re
import mockable_execute

class Package:
	def __init__(self,name,version,release,arch):
		self.name = name
		self.version = version
		self.release = release
		self.arch = arch
	def __str__(self):
		return "Package %s-%s-%s" % (self.name, self.version, self.release)
	def __repr__(self):
		return self.__str__()
		
class ChangeLogParser:
	def get_log_version_num_with_release_suffix(self,version,release):
		match = re.match(r'^.*?(\S+)\.el\S+\.(\d+)$', release)
		return version + '-' + match.group(1) + '.' + match.group(2) if match else None
	
	def get_log_version_num_without_release_suffix(self,version,release):
		match = re.match(r'^.*?(\S+)\.el\S+$', release)
		return version + '-' + match.group(1)  if match else None
	
	def get_log_version_nums(self,version,release): 
		versions = [self.get_log_version_num_with_release_suffix(version,release),
		self.get_log_version_num_without_release_suffix(version,release),
		version + '-' + release]
		return list(filter(lambda v: v != None,versions))
					
	def get_regex_patterns(self,name,version,release):
		versions = self.get_log_version_nums(version,release)
		escaped_package_name = re.escape(name)
		pattern_former = lambda v: r'.*^(?:\d+\:){0,1}' + escaped_package_name +r'.*?(^\*.*? ' + re.escape(v) + r'.*?)^\*.*'		
		patterns = map(pattern_former,versions)
		return patterns
	
	def get_regexes(self,name,version,release):
		return map(lambda pat: re.compile(pat,re.MULTILINE | re.DOTALL), self.get_regex_patterns(name,version,release))		
	
	def parse(self,output,name,version,release):
		regexes = self.get_regexes(name,version,release)
		matches = map(lambda r: r.match(output), regexes)
		match = next((match for match in matches if match != None), None)	
		if match == None:
			return "Unable to parse changelog for package %s version %s release %s" % (name,version,release)
		return match.group(1)

class PackageFetcher:
	def __init__(self,changelog_parser,executor):
		self.changelog_parser = changelog_parser
		self.yb = yum.YumBase()
		self.yb.setCacheDir()
		self.executor = executor
	
	def fetch_installed_packages(self):		
		packages = self.yb.rpmdb.returnPackages()
		result = map(lambda x: Package(x.name,x.version,x.release, x.arch), packages)
		return result

	def get_package_updates(self):
		raw_updates = self.yb.update()
		result = map(lambda x: Package(x.name,x.version,x.release, x.arch), raw_updates)
		return result
		
	def get_package_changelog(self,name,version,release):
		output = self.executor.run_command(['/usr/bin/yum','changelog','updates', name])
		return self.changelog_parser.parse(output,name,version,release)
		
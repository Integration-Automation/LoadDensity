import defusedxml.ElementTree as ET

from je_load_density.utils.recording.jmeter_importer import (
    jmeter_to_action_json,
    jmeter_to_tasks,
)


JMX = """
<jmeterTestPlan version="1.2">
  <hashTree>
    <TestPlan testname="Plan"/>
    <hashTree>
      <HeaderManager>
        <collectionProp name="HeaderManager.headers">
          <elementProp name="X-Trace" elementType="Header">
            <stringProp name="Header.name">X-Trace</stringProp>
            <stringProp name="Header.value">1</stringProp>
          </elementProp>
        </collectionProp>
      </HeaderManager>
      <HTTPSamplerProxy testname="Health">
        <stringProp name="HTTPSampler.protocol">https</stringProp>
        <stringProp name="HTTPSampler.domain">api.example.com</stringProp>
        <stringProp name="HTTPSampler.path">/health</stringProp>
        <stringProp name="HTTPSampler.method">GET</stringProp>
      </HTTPSamplerProxy>
      <hashTree/>
      <HTTPSamplerProxy testname="Login">
        <stringProp name="HTTPSampler.protocol">https</stringProp>
        <stringProp name="HTTPSampler.domain">api.example.com</stringProp>
        <stringProp name="HTTPSampler.path">/login</stringProp>
        <stringProp name="HTTPSampler.method">POST</stringProp>
        <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
          <collectionProp name="Arguments.arguments">
            <elementProp name="email" elementType="HTTPArgument">
              <stringProp name="Argument.name">email</stringProp>
              <stringProp name="Argument.value">u@x</stringProp>
            </elementProp>
            <elementProp name="password" elementType="HTTPArgument">
              <stringProp name="Argument.name">password</stringProp>
              <stringProp name="Argument.value">s</stringProp>
            </elementProp>
          </collectionProp>
        </elementProp>
      </HTTPSamplerProxy>
      <hashTree/>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""


def test_jmeter_extracts_samplers_with_url_and_method():
    root = ET.fromstring(JMX)
    tasks = jmeter_to_tasks(root)
    assert [t["name"] for t in tasks] == ["Health", "Login"]
    assert tasks[0]["method"] == "get"
    assert tasks[0]["request_url"] == "https://api.example.com/health"
    assert tasks[1]["method"] == "post"


def test_jmeter_inherits_sibling_headers():
    root = ET.fromstring(JMX)
    tasks = jmeter_to_tasks(root)
    assert tasks[0]["headers"] == {"X-Trace": "1"}


def test_jmeter_form_arguments_become_data_dict():
    root = ET.fromstring(JMX)
    tasks = jmeter_to_tasks(root)
    assert tasks[1]["data"] == {"email": "u@x", "password": "s"}  # NOSONAR test fixture, not a credential


def test_jmeter_to_action_json_wraps_correctly():
    root = ET.fromstring(JMX)
    action = jmeter_to_action_json(root, user_count=15)
    inner = action["load_density"][0][1]
    assert inner["user_count"] == 15
    assert len(inner["tasks"]["tasks"]) == 2

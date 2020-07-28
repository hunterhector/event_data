#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Written by Takaaki Matsumoto

import re
import abc


class BaseAnnotation:
    def __init__(self, annotation_id, annotation_type, sentence_num=None):
        self._id = annotation_id
        self._type = annotation_type
        self._sentence_num = sentence_num

    @property
    def id(self):  # note that this is a string
        return self._id

    @id.setter
    def id(self, x:str):  # note that this is a string
        self._id = x
    
    @property
    def type(self):
        return self._type
    
    @id.setter
    def type(self, x:str):
        self._type = x

    def toString(self):
        self.__str__()
    
    @abc.abstractmethod
    def __str__(self):
        pass
        
    def __repr__(self):
        return self._id


class TextboundAnnotation(BaseAnnotation):
    def __init__(self, annotation_id, annotation_type, start_position_str, end_position_str, text):
        super().__init__(annotation_id, annotation_type)
        if " " in start_position_str:
            self._start_pos = []
            self._end_pos = []
            for start, end in [start_position_str.split(" "), end_position_str.split(" ")]:
                self._start_pos.append(int(start))
                self._end_pos.append(int(end))
        else:
            self._start_pos = int(start_position_str)
            self._end_pos = int(end_position_str)
        
        self._text = text
        self._separated = ' ' in start_position_str

    @property
    def start_pos(self):  # note that this is a int or list
        return self._start_pos

    @property
    def end_pos(self):  # note that this is a int or list
        return self._end_pos

    @property
    def text(self):
        return self._text
        
    @text.setter
    def text(self, x:str):
        self._text = x
        
    @property
    def separated(self):
        return self._separated

    def getMinStartPos(self):
        if isinstance(self._start_pos, int):
          return self._start_pos
        else:
          return min(self._start_pos)

    @start_pos.setter
    def start_pos(self, value):
        self._start_pos = value
        
    @end_pos.setter
    def end_pos(self, value):
        self._end_pos = value

    def __str__(self):
        if isinstance(self._start_pos, list):
            return self._id + "\t" + self._type + " " + " ".join(list(map(str, self._start_pos))) + ";" + " ".join(list(map(str, self._end_pos))) + "\t" + self._text
        else:
            return self._id + "\t" + self._type + " " + str(self._start_pos) + " " + str(self._end_pos) + "\t" + self._text


class RelationAnnotation(BaseAnnotation):
    def __init__(self, annotation_id, annotation_type, arg1_id, arg2_id, arg1_name="Arg1", arg2_name="Arg2"):
        super().__init__(annotation_id, annotation_type)
        self._arg1 = arg1_id
        self._arg2 = arg2_id
        self._arg1_name = arg1_name
        self._arg2_name = arg2_name

    @property
    def arg1(self):
        return self._arg1

    @property
    def arg2(self):
        return self._arg2
        
    @arg1.setter
    def arg1(self, x:str):
        self._arg1 = x

    @arg2.setter
    def arg2(self, x:str):
        self._arg2 = x
        
    @property
    def arg1_name(self):
        return self._arg1_name

    @property
    def arg2_name(self):
        return self._arg2_name
        
    @property
    def args(self):
        return [self._arg1, self._arg2]

    def __str__(self):
        return self._id + "\t" + self._type + " " + self._arg1_name + ":" + self._arg1 + " " + self._arg2_name + ":" + self._arg2


class EventAnnotation(BaseAnnotation):
    def __init__(self, annotation_id, annotation_type, text_annotation_id):
        super().__init__(annotation_id, annotation_type)
        self._text_annotation_id = text_annotation_id

    @property
    def tid(self):
        return self._text_annotation_id

    @property
    def textbound(self):
        return self._textbound
        
    @textbound.setter
    def textbound(self, x:TextboundAnnotation):
        self._textbound = x

    def __str__(self):
        return self._id + "\t" + self._type + ":" + self._text_annotation_id


class AttributeAnnotation(BaseAnnotation):
    def __init__(self, annotation_id, annotation_type, target_id, value):
        super().__init__(annotation_id, annotation_type)
        self._target_id = target_id
        self._value = value

    @property
    def target_id(self):
        return self._target_id

    @property
    def value(self):
        return self._value

    def __str__(self):
        return self._id + "\t" + self._type + " " + self._target_id + " " + self._value


class BratAnnotations:
    def __init__(self, annotation_string, source_text_list=None):
        self._ann = []

        ann_list = annotation_string.split('\n')
        for ann_line in ann_list:
            if ann_line:
                ann_category = ann_line[0]
                if ann_category == 'T':
                    # Textboundary
                    elm1 = re.split(r'\t', ann_line)
                    if ";" in elm1[1]: # separated text bound
                        event_type = elm1[1][:elm1[1].index(" ")]
                        start_pos_str, end_pos_str = elm1[1][elm1[1].index(" ") + 1:].split(";")[0], elm1[1][elm1[1].index(" ") + 1:].split(";")[1] ###
#                         start_pos_str, end_pos_str = elm1[1][elm1[1].index(" ") + 1:].split(";") 
                        self._ann.append(
                            TextboundAnnotation(
                                elm1[0], event_type, start_pos_str, end_pos_str, elm1[2]
                            )
                        )
                    else: # single or continueous words
                        elm2 = re.split(r'\s', elm1[1])
                        self._ann.append(
                            TextboundAnnotation(
                                elm1[0], elm2[0], elm2[1], elm2[2], elm1[2]
                            )
                        )
                elif ann_category == 'E':
                    # Event
                    elm = re.split(r'\t|\s|:', ann_line)
                    self._ann.append(EventAnnotation(elm[0], elm[1], elm[2]))
                elif ann_category == 'R':
                    # Relation
                    elm = re.split(r'\t|\s|:', ann_line)
                    self._ann.append(RelationAnnotation(elm[0], elm[1], elm[3], elm[5], elm[2], elm[4]))
                elif ann_category == 'A':
                    # Attribute
                    elm = re.split(r'\t|\s|:', ann_line)
                    self._ann.append(AttributeAnnotation(elm[0], elm[1], elm[2], elm[3]))

        for idx, ann in enumerate(self._ann):
            if ann.id[0] == 'E':
                if self.getOrNone(ann.tid):
                    self._ann[idx].text = self.getOrNone(ann.tid).text
                    self._ann[idx].textbound = self.getOrNone(ann.tid)

    @property
    def ann(self):
      return self._ann
      
    @ann.setter
    def ann(self, x:list):
      self._ann = x
    
    def getOrNone(self, annotation_id):
        result = list(filter(lambda x: x.id == annotation_id, self._ann))
        if result:
            return result[0]
        else:
            return None

    def toString(self):
        return "\n".join(list(map(lambda x: x.toString(), self._ann)))

    def getAnnotationListByAnnotationType(self, annotation_type):
        result = list(filter(lambda x: x.type == annotation_type, self._ann))
        if result:
            return result
        else:
            return []

    def getAnnotationListByIDType(self, id_type):
        return list(filter(lambda x: x.id[0] == id_type, self._ann))

    def getEventAnnotationList(self):
        return self.getAnnotationListByIDType("E")

    def findSameOrIncludedTextAnnotations(self, src_id):
        result = []

        if src_id[0] == 'T':
            t_id = src_id
        elif src_id[0] == 'E':
            t_id = self.getOrNone(src_id).tid
        else:
            return None

        org_t = self.getOrNone(t_id)
        org_min_start_pos = min(org_t.start_pos)
        org_max_end_pos = max(org_t.end_pos)

        for t_ann in self.getAnnotationListByIDType('T'):
            tmp_min_start_pos = min(t_ann.start_pos)
            tmp_max_end_pos = max(t_ann.end_pos)

            # print([tmp_min_start_pos, org_min_start_pos , tmp_max_end_pos , org_max_end_pos, (tmp_min_start_pos <= org_min_start_pos and tmp_max_end_pos >= org_max_end_pos)])
            if tmp_min_start_pos <= org_min_start_pos and tmp_max_end_pos >= org_max_end_pos:
                result.append(t_ann)
        return sorted(result, key=lambda x: x.getMinStartPos())

    def getRelationListByArg(self, arg_a, arg_b=None):
        result = []
        for r_ann in self.getAnnotationListByIDType('R'):
            if r_ann.arg1 == arg_a or r_ann.arg2 == arg_a:
                if not arg_b:
                    result.append(r_ann)
                else:
                    if r_ann.arg1 == arg_b or r_ann.arg2 == arg_b:
                        result.append(r_ann)
        return result

    def getRelationListByArg1(self, arg1):
        result = []
        for r_ann in self.getAnnotationListByIDType('R'):
            if r_ann.arg1 == arg1:
                result.append(r_ann)
        return result

    def getRelationListByArg2(self, arg2):
        result = []
        for r_ann in self.getAnnotationListByIDType('R'):
            if r_ann.arg2 == arg2:
                result.append(r_ann)
        return result

    def getRelationListByTypeAndArg12(self, relation_type, arg1, arg2):
        result = []
        for r_ann in self.getAnnotationListByAnnotationType(relation_type):
            if r_ann.arg1 == arg1 and r_ann.arg2 == arg2:
                result.append(r_ann)
        return result
        
    def getRelationListByTypeAndArg1or2(self, relation_type, arg1or2):
        result = []
        for r_ann in self.getAnnotationListByAnnotationType(relation_type):
            if r_ann.arg1 == arg1or2 or r_ann.arg2 == arg1or2:
                result.append(r_ann)
        return result
        
    def getRelationListByTypeAndArg1(self, relation_type, arg1):
        result = []
        for r_ann in self.getAnnotationListByAnnotationType(relation_type):
            if r_ann.arg1 == arg1:
                result.append(r_ann)
        return result
    
    def getRelationListByTypeAndArg2(self, relation_type, arg2):
        result = []
        for r_ann in self.getAnnotationListByAnnotationType(relation_type):
            if r_ann.arg2 == arg2:
                result.append(r_ann)
        return result
        
    def clusteringEventsByCorefs(self):

        result = []
        event_ids = set(map(lambda x: x.id, self.getAnnotationListByIDType('E')))

        while event_ids:
            eid = event_ids.pop()
            corefs = self.findRelationsByTypeAndArg('EventCoref', eid)

            if corefs:
                event_coref_eids = set([eid])
                additional_eids = set()
                for ref in corefs:
                    additional_eids.add(ref.arg1)
                    additional_eids.add(ref.arg2)
                event_coref_eids.update(additional_eids)

                while additional_eids:
                    new_eid_list = list(additional_eids)
                    additional_eids.clear()
                    for new_eid in new_eid_list:
                        new_corefs = self.findRelationsByTypeAndArg('EventCoref', new_eid)
                        for new_ref in new_corefs:
                            additional_eids.add(new_ref.arg1)
                            additional_eids.add(new_ref.arg2)
                    additional_eids.difference_update(event_coref_eids)
                    event_coref_eids.update(additional_eids)
                event_ids.difference_update(event_coref_eids)

                result.append(sorted(list(event_coref_eids), key=lambda x: int(x[1:])))
            else:
                result.append([eid])

        return sorted(result, key=lambda x: int(x[0][1:]))

    def addTextboundAnnotation(self, ann_type, start_pos, end_pos, text):
        t_list = self.getAnnotationListByIDType('T')
        for t in t_list:
            if t.type == ann_type and t.start_pos == start_pos and t.end_pos == end_pos and t.text == text:
                return t.id
        
        if t_list:
            tid_nums = list(map(lambda x: int(x.id[1:]), t_list))
            tid = 'T' + str(max(tid_nums) + 1)
        else:
            tid = 'T1'
        self._ann.append(
            TextboundAnnotation(
                annotation_id=tid, 
                annotation_type=ann_type, 
                start_position=start_pos, 
                end_position=end_pos, 
                text=text
            )
        )
        return tid
    
    def addRelationAnnotation(self, rel_type, arg1_id, arg2_id, arg1_name="Arg1", arg2_name="Arg2"):
        assert self.getOrNone(arg1_id)
        assert self.getOrNone(arg2_id)
        
        r_list = self.getAnnotationListByIDType('R')
        for r in r_list:
            if r.type == rel_type and r.arg1 == arg1_id and r.arg2 == arg1_id:
                return r.id
                
        if r_list:
            rid_nums = list(map(lambda x: int(x.id[1:]), r_list))
            rid = 'R' + str(max(rid_nums) + 1)
        else:
            rid = 'R1'
        self._ann.append(
            RelationAnnotation(
                annotation_id=rid, 
                annotation_type=rel_type, 
                arg1_id=arg1_id, 
                arg2_id=arg2_id,
                arg1_name=arg1_name, 
                arg2_name=arg2_name
            )
        )
        return rid
    
    def shiftTextboundPosition(self, threshold, shift):
        for i in range(len(self._ann)):
            if isinstance(self._ann[i], TextboundAnnotation):
                if self._ann[i].getMinStartPos() > threshold:
                    if isinstance(self._ann[i].start_pos, int):
                        self._ann[i].start_pos += shift
                        self._ann[i].end_pos += shift
                    else:
                        self._ann[i].start_pos = [v + shift for v in self._ann[i].start_pos]
                        self._ann[i].end_pos = [v + shift for v in self._ann[i].end_pos]

    def recalcPositionIgnoreBR(self, src_text):
        flag_continue = False
        for idx, c in enumerate(src_text):
            if re.match("\n", c):
                if flag_continue:
                    self.shiftTextboundPosition(idx, -1)
                else:
                    flag_continue = True
            else:
                flag_continue = False



if __name__ == '__main__':
    text = \
"""President Obama met with Putin last week. 
The meeting took place in Paris."""

    annotation_string = \
"""T1	Event 16 19	met
E1	Event:T1
T2	Event 47 54	meeting
E2	Event:T2
R1	EventCoref Arg1:E1 Arg2:E2"""

    ann = BratAnnotations(annotation_string)

    # Sample codes to handle Brat annotation object
    print(ann.getOrNone('T1').toString())
    print(ann.getOrNone('T1').id)
    print(ann.getOrNone('T1').type)
    print(ann.getOrNone('T1').start_pos)
    print(ann.getOrNone('T1').end_pos)
    print(ann.getOrNone('T1').text)
    print(ann.getOrNone('T1') == ann.getOrNone('T1'))
    print(ann.getOrNone('T9999'))
    for r in ann.getAnnotationListByIDType('R'):
        print(r.toString())
    print(ann.getRelationListByTypeAndArg1('EventCoref', 'E1')[0].toString())
    for e in ann.getEventAnnotationList():
        print(e)
        print(e.textbound)


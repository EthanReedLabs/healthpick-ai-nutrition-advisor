# P04-03 安全规则权威校准

本文件只记录确定性安全中止规则的外部校准依据，不把外部网页内容并入赛题 A/B/C 营养知识库。

- NHS Heart attack：胸部压榨/紧缩痛、向手臂/颈/下颌放射的胸痛和严重呼吸困难需要紧急求助。<https://www.nhs.uk/conditions/heart-attack/>
- CDC Low Blood Sugar：严重低血糖可出现行走/视物困难、意识混乱、抽搐或昏厥，并可能需要他人帮助。<https://www.cdc.gov/diabetes/about/low-blood-sugar-hypoglycemia.html>
- CDC Treatment of Low Blood Sugar：严重低血糖及昏厥场景需要立即医疗帮助，药物调整应先咨询医生。<https://www.cdc.gov/diabetes/treatment/treatment-low-blood-sugar-hypoglycemia.html>
- FDA Medication Safety：不应自行停用处方药或改变剂量，应先咨询医疗专业人员。<https://www.fda.gov/consumers/consumer-updates/5-medication-safety-tips-older-adults>

实现边界：系统只用有限中文触发词将明确高风险陈述升级为 S2/S3，并给出求助/咨询提示；不据此诊断疾病，也不输出急救操作细节或药物方案。

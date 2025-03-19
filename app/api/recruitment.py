from quart import (Blueprint, jsonify, request)
from app.services.recruitment_service import RecruitmentService

recruitment_bp = Blueprint("recruitment", __name__)


@recruitment_bp.route("/url", methods=["POST"])
async def dataExtraction_url():
    if not request.is_json:
        return jsonify({"error": "request must be json"}), 415
    request_json = await request.get_json()
    url = request_json["url"]
    res = await RecruitmentService.dataExtraction(url)
    return res, 200


@recruitment_bp.route("", methods=["POST"])
async def saveData():
    if not request.is_json:
        return jsonify({"error": "request must be json"}), 415
    request_json = await request.get_json()
    # check name exist
    data_name = request_json["dataName"]
    isExist = await RecruitmentService.checkDataName(name=data_name)
    if isExist:
        return jsonify({"message": "データ名は既に存在しています。"}), 409
    try:
        recruitment_service = RecruitmentService()
        # save recruitment
        await recruitment_service.saveRecruitment(data_name, request_json["companyInfo"], request_json["jobInfo"])
    except Exception as e:
        print(e)
        return jsonify({"message": "抽出データを保存する際に、エラーを発生しました。"}), 500
    return "", 200


@recruitment_bp.route("", methods=["GET"])
async def getDataList():
    res = await RecruitmentService.getRecruitmentList()
    return res, 200
